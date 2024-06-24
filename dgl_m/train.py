import torch
import mlflow
import pprint
import os
import copy

from .data_utils import get_loader
from .train_utils import get_loss_fn, get_model

from loguru import logger
from tqdm import tqdm
from sklearn.metrics import classification_report, f1_score
# from torch_geometric.nn import summary

def node_classification_step(mode: str, epoch, loader, model, loss_fn, optimizer, enable_tqdm, sampling_strategy, batch_size, device="cpu", multilabel=False, threshold=0):
    if mode == "test":
        model.eval()
    else:
        total_loss = 0
        total_num = 0
        if mode == "train":
            model.train()
        elif mode == "val":
            model.eval()

    predictions = []
    truths = []
    bar = tqdm(loader, total=len(loader), disable=not enable_tqdm)
    for input_nodes, output_nodes, mfgs in bar:

        if mode == "train":
            optimizer.zero_grad()

        if sampling_strategy in ["SAGE", None, "None"]:
            mask = torch.arange(batch_size, device=device)
        elif sampling_strategy in ["GraphBatching"]:
            mask = torch.ones(mfgs[0].srcdata['feat'].shape[0], dtype=bool)

        targets = mfgs[-1].dstdata['label']
        inputs = mfgs[0].srcdata['feat']
        outputs = model(mfgs, inputs)

        if multilabel:
            preds = outputs > threshold
        else:
            preds = outputs.argmax(dim=-1)

        predictions.append(preds)
        truths.append(targets)

        if mode != "test":
            loss = loss_fn(outputs, targets)
            loss.backward()

            if mode == "train":
                optimizer.step()

            loss = loss.detach().cpu()
            num_targets = outputs.numel()
            total_loss += loss * num_targets
            total_num += num_targets
            bar.set_description(f"{mode}_loss={loss:<8.6g}")

    # Metrics
    predictions = torch.cat(predictions, dim=0).detach().cpu().numpy()
    truths = torch.cat(truths, dim=0).detach().cpu().numpy()

    if mode != "test":
        avg_loss = total_loss/total_num
        mlflow.log_metric(f"{mode} loss", avg_loss, epoch)

    f1 = f1_score(truths, predictions, average="micro")
    mlflow.log_metric(f"{mode} F1", f1, epoch)

    if mode == "train":
        return avg_loss, f1
    elif mode == "val":
        return avg_loss, f1
    elif mode == "test":
        return f1, truths, predictions

def train_gnn(config):

    general_config = config["general_config"]
    device = general_config["device"]
    dataset_config = config["dataset_collections"][config["dataset"]]

    # Initialize MLflow Logging
    run_name = f"{config['model']}"
    run = mlflow.start_run(run_name=run_name)
    mlflow.set_tag(
        "base model", config["model_collections"][config["model"]]["base_model"])
    mlflow.set_tag("dataset", config["dataset"])
    logger.info(f"Launching run: {run.info.run_name}")

    # Log hyperparameters
    params = config["hyperparameters"]
    params.update(config["model_collections"][config["model"]])
    params_str = pprint.pformat(params)
    general_config_str = pprint.pformat(general_config)
    logger.info(f"General configurations:\n{general_config_str}")
    logger.info(f"Hyperparameters:\n{params_str}")
    mlflow.log_params(general_config)
    mlflow.log_params(params)

    # Get loaders
    train_loader, val_loader, test_loader = get_loader(config)

    # Setup loss function
    loss_fn = get_loss_fn(config, train_loader, reduction='mean')

    # Get model
    model = get_model(config)
    model.to(device).reset_parameters()

    # Setup save directory for optimizer states
    if general_config["save_model"]:
        save_path = os.path.join(
            "logs/tmp", f"{run.info.run_name}-Optimizer-{run.info.run_id}.tar")
        if not os.path.exists(os.path.dirname(save_path)):
            os.makedirs(os.path.dirname(save_path))

    # Summary logging
    # sample_batch = None
    # for input_nodes, output_nodes, blocks in train_loader:
    #     for batch in blocks:
    #         sample_batch = batch
    #         break
    #     break
    # summary_str = summary(model, sample_batch.ndata['feat'], torch.stack(sample_batch.edges()))
    # logger.info("Model Summary:\n" + summary_str)
    # with open("logs/tmp/model_summary.txt", "w") as out_file:
    #     out_file.write(summary_str)
    # mlflow.log_artifact("logs/tmp/model_summary.txt")

    # Setup Optimizer
    optimizer = torch.optim.Adam(
        model.parameters(), lr=params["lr"], weight_decay=params["weight_decay"])

    # Setup metrics
    criterion = general_config["criterion"].lower()
    if criterion == "loss":
        best_value = -2147483647
    elif criterion == "f1":
        best_value = -1

    # Training loop
    patience = general_config["patience"]
    if patience == None:
        patience = general_config["num_epochs"]

    # Setup training steps according to task type
    sampling_strategy = config["general_config"]["sampling_strategy"]
    if dataset_config["task_type"] == "single-label-NC":
        run_step = lambda *args, **kwargs: node_classification_step(*args, model=model, batch_size=params['batch_size'], loss_fn=loss_fn, optimizer=optimizer, enable_tqdm=general_config["tqdm"], sampling_strategy=sampling_strategy, device=device, **kwargs)
    elif dataset_config["task_type"] == "multi-label-NC":
        run_step = lambda *args, **kwargs: node_classification_step(*args, model=model, batch_size=params['batch_size'], loss_fn=loss_fn, optimizer=optimizer, enable_tqdm=general_config["tqdm"], sampling_strategy=sampling_strategy, device=device, multilabel=True, threshold=0, **kwargs)

    best_epoch = 0
    for epoch in range(1, 1+general_config["num_epochs"]):
        if general_config["tqdm"]:
            print(f"Epoch {epoch}:")
        # Batch training
        train_loss, train_f1 = run_step("train", epoch, train_loader)

        # Validation
        val_loss, val_f1 = run_step("val", epoch, val_loader)

        # Test
        test_f1, truths, predictions = run_step("test", epoch, test_loader)

        logger.info(
            f"Epoch {epoch}: train_loss={train_loss:<8.6g}, train_f1={train_f1:<8.6g}, val_loss={val_loss:<8.6g}, val_f1={val_f1:<8.6g}, test_f1={test_f1:<8.6g}")

        # Best model
        if criterion == "loss":
            criterion_value = -val_loss
        elif criterion == "f1":
            criterion_value = val_f1

        if criterion_value > best_value:
            best_value = criterion_value
            mlflow.log_metric("Best Test F1", test_f1, epoch)

            best_model_state_dict = copy.deepcopy(model.state_dict())
            best_report = classification_report(
                truths, predictions, zero_division=0)
            best_epoch = epoch

            if general_config["save_model"]:
                torch.save(
                    {
                        'epoch': epoch,
                        'optimizer_state_dict': optimizer.state_dict(),
                    },
                    save_path
                )

        # Early Stopping
        if epoch-best_epoch > patience:
            logger.info("Patience reached. Early stop the trainning.")
            break

    model.load_state_dict(best_model_state_dict)
    if general_config["save_model"]:
        mlflow.pytorch.log_model(model, "Best Model")
        mlflow.log_artifact(save_path, "Optimizer States")
        os.remove(save_path)

    with open("logs/tmp/test_report.txt", "w") as out_file:
        out_file.write(best_report)
    mlflow.log_artifact("logs/tmp/test_report.txt")

    logger.info(f"Best model report:\n{best_report}")

    mlflow.end_run()
