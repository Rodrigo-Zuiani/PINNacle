import argparse
import time
import os
from trainer import Trainer

os.environ["DDEBACKEND"] = "pytorch"

import numpy as np
import matplotlib.pyplot as plt
import torch
import deepxde as dde
from src.model.laaf import DNN_GAAF, DNN_LAAF
from src.optimizer import MultiAdam, LR_Adaptor, LR_Adaptor_NTK, Adam_LBFGS
from src.pde.electromag import Magnetism_2D
from src.utils.args import parse_hidden_layers, parse_loss_weight
from src.utils.callbacks import TesterCallback, PlotCallback, LossCallback
from src.utils.rar import rar_wrapper

pde_config = Magnetism_2D

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PINNBench trainer')
    parser.add_argument('--name', type=str, default="benchmark")
    parser.add_argument('--device', type=str, default="0")  # set to "cpu" enables cpu training 
    parser.add_argument('--seed', type=int, default=None)
    parser.add_argument('--hidden-layers', type=str, default="100*5")
    parser.add_argument('--loss-weight', type=str, default="")
    parser.add_argument('--lr', type=float, default=1e-3)
    parser.add_argument('--iter', type=int, default=20000)
    parser.add_argument('--log-every', type=int, default=100)
    parser.add_argument('--plot-every', type=int, default=2000)
    parser.add_argument('--repeat', type=int, default=1)
    parser.add_argument('--method', type=str, default="adam")

    command_args = parser.parse_args()

    seed = command_args.seed
    if seed is not None:
        dde.config.set_random_seed(seed)
    date_str = time.strftime('%m.%d-%H.%M.%S', time.localtime())
    trainer = Trainer(f"{date_str}-{command_args.name}", command_args.device)

    def get_model_dde():
        if isinstance(pde_config, tuple):
            pde = pde_config[0](**pde_config[1])
        else:
            pde = pde_config()
        
        # pde.training_points()
        if command_args.method == "gepinn":
            pde.use_gepinn()

        net = dde.nn.FNN([pde.input_dim] + parse_hidden_layers(command_args) + [pde.output_dim], "tanh", "Glorot normal")
        if command_args.method == "laaf":
            net = DNN_LAAF(len(parse_hidden_layers(command_args)) - 1, parse_hidden_layers(command_args)[0], pde.input_dim, pde.output_dim)
        elif command_args.method == "gaaf":
            net = DNN_GAAF(len(parse_hidden_layers(command_args)) - 1, parse_hidden_layers(command_args)[0], pde.input_dim, pde.output_dim)
        net = net.float()

        loss_weights = parse_loss_weight(command_args)
        if loss_weights is None:
            loss_weights = np.ones(pde.num_loss)
        else:
            loss_weights = np.array(loss_weights)

        opt = torch.optim.Adam(net.parameters(), command_args.lr)
        if command_args.method == "multiadam":
            opt = MultiAdam(net.parameters(), lr=1e-3, betas=(0.99, 0.99), loss_group_idx=[pde.num_pde])
        elif command_args.method == "lra":
            opt = LR_Adaptor(opt, loss_weights, pde.num_pde)
        elif command_args.method == "ntk":
            opt = LR_Adaptor_NTK(opt, loss_weights, pde)
        elif command_args.method == "lbfgs":
            opt = Adam_LBFGS(net.parameters(), switch_epoch=5000, adam_param={'lr':command_args.lr})

        model = pde.create_model(net)
        model.compile(opt, loss_weights=loss_weights)
        if command_args.method == "rar":
            model.train = rar_wrapper(pde, model, {"interval": 1000, "count": 1})
        # the trainer calls model.train(**train_args)
        return model

    def get_model_others():
        model = None
        # create a model object which support .train() method, and param @model_save_path is required
        # create the object based on command_args and return it to be trained
        # schedule the task using trainer.add_task(get_model_other, {training args})
        return model

    trainer.add_task(
        get_model_dde, {
            "iterations": command_args.iter,
            "display_every": command_args.log_every,
            "callbacks": [
                TesterCallback(log_every=command_args.log_every),
                PlotCallback(log_every=command_args.plot_every, fast=True),
                LossCallback(verbose=True),
            ]
        }
    )

    trainer.setup(__file__, seed)
    trainer.set_repeat(command_args.repeat)
    trainer.train_all()
    trainer.summary()

    data = np.loadtxt(f"runs/{date_str}-{command_args.name}/0-0/model_output.txt", comments="#", delimiter=" ")

    pde = pde_config()
    new_data = pde.geom.random_points(5000)

    model = get_model_dde()
    #model.load_state_dict(torch.load(f"runs/{date_str}-{command_args.name}/0-0/{command_args.iter}.pt", weights_only=True))
    model.restore(f"runs/{date_str}-{command_args.name}/0-0/{command_args.iter}.pt")

    x, y, u, v = data[:, 0], data[:, 1], data[:, 2], data[:, 3]
    xy = data[:, 0:2]
    ref_uv = pde.ref_sol(xy)
    u_ref, v_ref = ref_uv[:, 0], ref_uv[:, 1]
    output = model.predict(new_data)
    x_new, y_new = new_data[:, 0], new_data[:, 1]
    u_inference, v_inference = output[:, 0], output[:, 1]

    color = np.sqrt((u)**2 + (v)**2)
    color_ref = np.sqrt((u_ref)**2 + (v_ref)**2)
    color_inference = np.sqrt((u_inference)**2 + (v_inference)**2)

    plt.subplot(2, 2, 1)
    plt.quiver(x, y, u_ref, v_ref, color_ref)
    plt.gca().set_aspect("equal")
    plt.title("Reference Solution Vectors")

    plt.subplot(2, 2, 2)
    plt.quiver(x, y, u, v, color)
    plt.gca().set_aspect("equal")
    plt.title("Model Output Vectors")

    plt.subplot(2, 1, 2)
    plt.quiver(x_new, y_new, u_inference, v_inference, color_inference)
    plt.gca().set_aspect("equal")
    plt.title("Inference Vectors")

    plt.tight_layout()
    plt.savefig(f"runs/{date_str}-{command_args.name}/0-0/vectors", dpi=300)
    plt.close()
