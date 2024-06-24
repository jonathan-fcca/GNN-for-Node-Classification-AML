import torch
import dgl.transforms as T

import dgl
from dgl.dataloading import NeighborSampler, DataLoader, GraphDataLoader

from loguru import logger



def get_data_SAGE(config):
    transform = T.Compose([T.RowFeatNormalizer()])
    if config["dataset"] in 'Cora':
        from dgl.data import CoraGraphDataset
        dataset = CoraGraphDataset('dataset', transform=transform)
    elif config["dataset"] in 'CiteSeer':
        from dgl.data import CiteseerGraphDataset
        dataset = CiteseerGraphDataset('dataset', transform=transform)
    elif config["dataset"] in 'PubMed':
        from dgl.data import PubmedGraphDataset
        dataset = PubmedGraphDataset('dataset', transform=transform)
    elif config["dataset"] in "Reddit":
        from dgl.data import RedditDataset
        dataset = RedditDataset('dataset', transform=transform)
    elif config['dataset'] in 'PPI':
        from dgl.data import PPIDataset
        dataset = (PPIDataset(mode='train', raw_dir='dataset', transform=transform), PPIDataset(mode='valid', raw_dir='dataset', transform=transform), PPIDataset(mode='test', raw_dir='dataset', transform=transform))
    else:
        logger.exception('Unsupported dataset.')
        
    general_config = config["general_config"]
    
    # For dataset containing one graph
    if len(dataset) == 1:
        data = dataset[0]
        if general_config["framework"] == "transductive":
            logger.info("Using data split for transductive training.")
            train_data = data
            val_data = data
            test_data = data
            general_config.pop("SAGE_inductive_option")

        elif general_config["framework"] == "inductive":
            if general_config["SAGE_inductive_option"] in ["default", "strict"]:
                logger.info("Using data split for strict inductive learning.")
                train_data = data.subgraph(data.ndata['train_mask'])
                val_data = data.subgraph(data.ndata['val_mask'])
                test_data = data.subgraph(data.ndata['test_mask'])
            elif general_config["SAGE_inductive_option"] == "soft":
                logger.info("Using data split for non-strict inductive learning.")
                train_data = data.subgraph(data.ndata['val_mask'])
                val_data = data
                test_data = data
                
    # For dataset containing multiple graphs. Strictly inductive learning by default.
    else:
        train_data, val_data, test_data = dataset

        train_data = dgl.batch(train_data)
        val_data = dgl.batch(val_data)
        test_data = dgl.batch(test_data)
        
        
        train_data.ndata['train_mask'] = torch.ones(train_data.num_nodes(), dtype=bool)
    
        val_data.ndata['val_mask'] = torch.ones(val_data.num_nodes(), dtype=bool)
    
        test_data.ndata['test_mask'] = torch.ones(test_data.num_nodes(), dtype=bool)
    
    return train_data, val_data, test_data


def get_loader_SAGE(train_data, val_data, test_data, config):
    model_config = config["model_collections"][config["model"]]
    num_neighbors = model_config.pop("num_neighbors")
    if isinstance(num_neighbors, int):
        num_neighbors = [num_neighbors] * model_config["num_layers"]
    elif isinstance(num_neighbors, list):
        num_neighbors = num_neighbors
        assert len(num_neighbors) == model_config["num_layers"]

    params = config["hyperparameters"]
    
    general_config = config["general_config"]

    logger.info(
        f"\ntrain_data={train_data}\nval_data={val_data}\ntest_data={test_data}")

    neighborsampler = NeighborSampler(num_neighbors)

    train_loader = DataLoader(
        graph=train_data,
        indices=train_data.nodes()[train_data.ndata['train_mask']],
        graph_sampler=neighborsampler,
        batch_size=params["batch_size"],
        num_workers=general_config["num_workers"],
        persistent_workers=general_config["persistent_workers"]
    )

    if not general_config["sample_when_predict"]:
        logger.warning(
            "sample_when_predict is set to be False. All neighbors will be used for aggregation when doing prediction in validation and testing.")
        num_neighbors = [-1] * model_config["num_layers"]
        neighborsampler = NeighborSampler(num_neighbors)

    val_loader = DataLoader(
        graph=val_data,
        indices=val_data.nodes()[val_data.ndata['val_mask']],
        graph_sampler=neighborsampler,
        batch_size=params["batch_size"],
        num_workers=general_config["num_workers"],
        persistent_workers=general_config["persistent_workers"],
    )

    test_loader = DataLoader(
        graph=test_data,
        indices=test_data.nodes()[test_data.ndata['test_mask']],
        graph_sampler=neighborsampler,
        batch_size=params["batch_size"],
        num_workers=general_config["num_workers"],
        persistent_workers=general_config["persistent_workers"],
    )
    

    return train_loader, val_loader, test_loader

def get_loader_no_sampling(train_data, val_data, test_data, config):
    model_config = config["model_collections"][config["model"]]

    logger.warning(
        "Sampling strategy is set to be None. Full graph will be used without mini-batching! Batch_size is ignored! ")
    num_neighbors = [-1] * model_config["num_layers"]
    model_config.pop("num_neighbors", None)

    general_config = config["general_config"]

    logger.info(
        f"\ntrain_data={train_data}\nval_data={val_data}\ntest_data={test_data}")

    neighborsampler = NeighborSampler(num_neighbors)

    train_loader = DataLoader(
        graph=train_data,
        indices=train_data.nodes()[train_data.ndata['train_mask']],
        graph_sampler=neighborsampler,
        batch_size=config['hyperparameters']['batch_size'],
        num_workers=general_config["num_workers"],
        persistent_workers=general_config["persistent_workers"],
    )

    val_loader = DataLoader(
        graph=val_data,
        indices=val_data.nodes()[val_data.ndata['val_mask']],
        graph_sampler=neighborsampler,
        batch_size=config['hyperparameters']['batch_size'],
        num_workers=general_config["num_workers"],
        persistent_workers=general_config["persistent_workers"],
    )

    test_loader = DataLoader(
        graph=test_data,
        indices=test_data.nodes()[test_data.ndata['test_mask']],
        graph_sampler=neighborsampler,
        batch_size=config['hyperparameters']['batch_size'],
        num_workers=general_config["num_workers"],
        persistent_workers=general_config["persistent_workers"],
    )

    return train_loader, val_loader, test_loader

def get_data_graph_batch(config):
    transform = T.Compose([T.RowFeatNormalizer()])
    if config["dataset"] == "PPI":
        from dgl.data import PPIDataset
        train_dataset = PPIDataset(mode='train', raw_dir='dataset', transform=transform)
        val_dataset = PPIDataset(mode='valid', raw_dir='dataset', transform=transform)
        test_dataset = PPIDataset(mode='test', raw_dir='dataset', transform=transform)
        
    return train_dataset, val_dataset, test_dataset


def get_loader_graph_batch(train_dataset, val_dataset, test_dataset, config):
    batch_size = config["hyperparameters"]["batch_size"]
    general_config = config["general_config"]
    
    train_loader = GraphDataLoader(
        train_dataset, 
        batch_size=batch_size,
        num_workers=general_config["num_workers"],
        persistent_workers=general_config["persistent_workers"],
        )
    val_loader = GraphDataLoader(
        val_dataset, 
        batch_size=batch_size,
        num_workers=general_config["num_workers"],
        persistent_workers=general_config["persistent_workers"],
        )
    test_loader = GraphDataLoader(
        test_dataset, 
        batch_size=batch_size,
        num_workers=general_config["num_workers"],
        persistent_workers=general_config["persistent_workers"],
        )
    
    return train_loader, val_loader, test_loader

def get_data(config):
    if config["general_config"]["sampling_strategy"] == 'SAGE':
        return get_data_SAGE(config)
    # elif config["general_config"]["sampling_strategy"] == 'SAINT':
    #     return get_data_SAINT(config)


def get_loader(config):
    sampling_strategy = config["general_config"]["sampling_strategy"]
    if sampling_strategy == 'SAGE':
        return get_loader_SAGE(*get_data_SAGE(config), config)
    # elif sampling_strategy == 'SAINT':
    #     return get_loader_SAINT(*get_data_SAINT(config), config)
    elif sampling_strategy == 'GraphBatching':
        return get_loader_graph_batch(*get_data_graph_batch(config), config)
    elif sampling_strategy == 'None' or sampling_strategy == None:
        return get_loader_no_sampling(*get_data_SAGE(config), config)