"""
Configurations

Priority of configuration:
Command line arguments > configuraions in model["overwirte"] > other configuration.
"""


class config:

    mode = None  # Will be overwritten as train/inference by command line.
    model = None  # Must be one of the model in model_collections
    dataset = None  # Must be one of the dataset in dataset_collections

    # MLflow tracking server configrations
    mlflow_config = {
        "tracking_uri": "http://127.0.0.1:8080/",
        "username": "admin",
        "password": "password",
        "experiment": "Default",
        "auth": True
    }

    general_config = {
        "framework": "transductive", # Must be transductive or inductive

        "sampling_strategy": "None",  # Must be choosen from sampling_strategy options

        # Used if sampling_strategy is SAGE; Must be choosen from SAGE_inductive_options
        "SAGE_inductive_option": "strict",

        # Enable to use sampling strategy when predicting (val, test, inference). Default: False.
        "sample_when_predict": False,

        "seed": 118010142,
        "device": "cpu",
        "tqdm": False,
        "save_model": True,
        "criterion": "loss",
        "num_epochs": 1000,
        "patience": 100,
        "num_workers": 2,
        "persistent_workers": True
    }

    # Hyperparameters
    hyperparameters = {
        # batch_size to infinity if memory allowed
        "batch_size": 512, 
        "lr": 5e-3,
        "weight_decay": 0.0005, # L2 regularization,
        
        "weighted_BCE": False, # Only useful for multi-label task.
    }

    """Options for difference experiment settings

    transductive: 
        The data split will follow a transductive manner. Training nodes can connected with validation nodes or testing nodes, though backward propogation is only applied on the loss computed by the training nodes.
        
    inductive:
        - If sampling_strategy is "SAGE":
            -  default or strict
                The data will be split to train_subgraph, val_subgraph, and test_subgraph. No message passing across the train. val, and test datasets is allowed.
            -  soft:
                Training nodes are cut off from validation nodes and testing nodes to form a training subgraph. However, when doing inference on the validation nodes and testing nodes, the edges  <Node_train, Node_val/Node_test>  and <Node_val, Node_test> can be used.
        - If sampling_strategy is "SAINT"
            TODO
        - If sampling_strategy is "None". string("None")!!!
            This should only happen when the framework is transductive. All neighbors will be used, so the model behaves like GCN. 
        - If sampling_strategy is "GraphBatching":
            Graph-level batching. This option is useful for dataset containing multiple graphs. Each graph will be regarded as one batch-element as a whole. E.g., batch_size = 2 will give each batch containing 2 graphs.
    """
    framework_options = [
        "transductive",
        "inductive"
    ]
    sampling_strategy_options = [
        "SAGE",  # use the inductive learning proposed by GraphSAGE
        "SAINT",  # use the inductive learning proposed by GraphSAINT
        "None", # only useful when GCN-like behaviors are desired.
        "GraphBatching",
    ]
    SAGE_inductive_options = [
        "default",
        "strict",
        "soft",
    ]

    # Model collections. Create the configuration of each model here.
    model_collections = {
        "GraphSAGE-mean": {
            "base_model": "GraphSAGE_PyG",
            "num_layers": 2,
            "num_neighbors": [25, 10],
            "hidden_node_channels": 256,
            "dropout": 0,
            "jk": None
        },
        
        "GraphSAGE-GCN-benchmark-trans":{
            "base_model": "GraphSAGE_PyG",
            "overwrite": {
                "framework": "transductive",
                "sampling_strategy": "None",
                "lr" : 5e-5,
                "weight_decay": 5e-4,
            },
            "num_layers": 2,
            "hidden_node_channels": 64,
            "dropout": 0,
            "aggr": "mean",
        },

        "GraphSAGE-DGL-mean":{
            "base_model": "GraphSAGE_DGL",
            "overwrite": {
                "framework": "transductive",
                "sampling_strategy": "None",
                "lr" : 5e-3,
                "weight_decay": 5e-4,
            },
            "num_layers": 2,
            "num_neighbors": [25, 10],
            "hidden_node_channels": 64,
            "dropout": 0.9,
            "jk": None,
            "aggr": "gcn",
        },

        # Transductive benchmark GAT of Planetoid; 
        # For PubMed: output_heads=8, lr=0.01, weight_decay=0.001
        "GAT-benchmark-trans": {
            "base_model": "GAT_Custom",
            "overwrite": {
                "framework": "transductive",
                "sampling_strategy": "None",
                "lr" : 5e-3,
                "weight_decay": 5e-4,
            },
            "hidden_node_channels_per_head": 8,
            "num_layers": 2,
            "heads": 8,
            "output_haeds": 1,
            "dropout": 0.6,
            "jk": None,
            "v2": False,
        },
        
        "GAT-SAGE-trans": {
            "base_model": "GAT_Custom",
            "overwrite": {
                "framework": "transductive",
                "sampling_strategy": "SAGE",
                "batch_size": 999999,
                "lr" : 5e-3,
                "weight_decay": 5e-4,
            },
            "hidden_node_channels_per_head": 8,
            "num_layers": 2,
            "num_neighbors": [25, 10],
            "heads": 8,
            "output_haeds": 1,
            "dropout": 0,
            "jk": None,
            "v2": False,
        },
        
        # Inductive benchmark GAT of PPI; 
        "GAT-benchmark-in": {
            "base_model": "GAT_Custom",
            "overwrite": {
                "framework": "inductive",
                "sampling_strategy": "GraphBatching",
                "batch_size": 2,
                "lr" : 5e-3,
                "weight_decay": 0,
            },
            "num_layers": 3,
            "heads": [4, 4],
            "hidden_node_channels_per_head": [256, 256],
            "output_haeds": 6,
            "dropout": 0,
            "jk": None,
            "v2": False,
            "skip_connection": True,
        },
        
        "GAT-PyG-in": {
            "base_model": "GAT_PyG",
            "overwrite": {
                "framework": "inductive",
                "sampling_strategy": "GraphBatching",
                "batch_size": 2,
                "lr" : 5e-3,
                "weight_decay": 0,
            },
            "num_layers": 3,
            "heads": 4,
            "hidden_node_channels_per_head": 256,
            "dropout": 0,
            "jk": None,
            "v2": False,
        },

        "GAT-benchmark-trans-DGL": {
            "base_model": "GAT_DGL_Custom",
            "overwrite": {
                "framework": "transductive",
                "sampling_strategy": "None",
                "lr" : 5e-3,
                "weight_decay": 5e-4,
            },
            "hidden_node_channels_per_head": 8,
            "num_layers": 2,
            "heads": 8,
            "output_haeds": 1,
            "dropout": 0.7,
            "jk": None,
            "v2": False,
        },

        "GIN": {

        }
    }

    # Dataset collections
    # Task type: 
    #  - "single-label-NC" : single label node classification
    #  - "multi-label-NC" : multi-label node classification
    dataset_collections = {
        "Cora": {
            "task_type": "single-label-NC",
            "num_node_features": 1433,
            "num_classes": 7
        },
        "CiteSeer": {
            "task_type": "single-label-NC",
            "num_node_features": 3703,
            "num_classes": 6
        },
        "PubMed": {
            "task_type": "single-label-NC",
            "num_node_features": 500,
            "num_classes": 3
        },
        "Reddit": {
            "task_type": "single-label-NC",
            "num_node_features": 602,
            "num_classes": 41
        },
        "Reddit2": {
            "task_type": "single-label-NC",
            "num_node_features": 602,
            "num_classes": 41
        },
        "Flickr": {
            "task_type": "single-label-NC",
            "num_node_features": 500,
            "num_classes": 7
        },
        "Yelp": {
            "task_type": "single-label-NC",
            "num_node_features": 300,
            "num_classes": 100
        },
        "AmazonProducts": {
            "task_type": "single-label-NC",
            "num_node_features": 200,
            "num_classes": 107
        },
        "PPI": {
            "task_type": "multi-label-NC",
            "num_node_features": 50,
            "num_classes": 121
        }
    }
