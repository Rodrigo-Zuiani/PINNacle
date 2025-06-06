import sys

import numpy as np

sys.path.insert(0, '.')
import problems
from active_schedulers import AllActiveSchedulerND, PointActiveSchedulerND, LineActiveSchedulerND, PlaneActiveSchedulerND, ManualActiveSchedulerND
from constants import Constants, get_subdomain_xs, get_subdomain_ws
from main import FBPINNTrainer, PINNTrainer
from trainersBase import train_models_multiprocess

sys.path.insert(0, 'pdes')
from heat import HeatComplex, HeatLongTime, HeatDarcy

plot_lims = (1.1, False)
random = False

def run_PINN():
    c = Constants(
        RUN="bench2_PINN_%s_%sh_%sl_%sb"%(P.name, n_hidden, n_layers, batch_size[0]),
        P=P,
        SUBDOMAIN_XS=subdomain_xs,
        BOUNDARY_N=boundary_n,
        Y_N=y_n,
        N_HIDDEN=n_hidden,
        N_LAYERS=n_layers,
        BATCH_SIZE=batch_size,
        RANDOM=random,
        N_STEPS=n_steps,
        BATCH_SIZE_TEST=batch_size_test,
        PLOT_LIMS=plot_lims,
        TEST_FREQ=1000,
        SUMMARY_FREQ=100,
    )
    PINNTrainer(c).train()

def run_FBPINN():
    grid = "x".join([str(len(sx)-1) for sx in subdomain_xs])
    bdw = "" if boundary_weight==-1 else "_bdw"+str(boundary_weight)
    c = Constants(
        RUN="bench2_%s_%s_%sh_%sl_%sb_%sw_%s"%(grid+bdw, P.name, n_hidden, n_layers, batch_size[0], width, A.name),
        P=P,
        SUBDOMAIN_XS=subdomain_xs,
        SUBDOMAIN_WS=subdomain_ws,
        BOUNDARY_N=boundary_n,
        Y_N=y_n,
        ACTIVE_SCHEDULER=A,
        ACTIVE_SCHEDULER_ARGS=args,
        N_HIDDEN=n_hidden,
        N_LAYERS=n_layers,
        BATCH_SIZE=batch_size,
        BOUNDARY_BATCH_SIZE=boundary_batch_size,
        BOUNDARY_WEIGHT=boundary_weight,
        RANDOM=random,
        N_STEPS=n_steps,
        BATCH_SIZE_TEST=batch_size_test,
        BOUNDARY_BATCH_SIZE_TEST=boundary_batch_size_test,
        PLOT_LIMS=plot_lims,
        TEST_FREQ=1000,
        SUMMARY_FREQ=200,
    )
    FBPINNTrainer(c).train()

name = "HeatLongTime"
if name=="HeatComplex":
    P = HeatComplex()
    subdomain_xs = [np.array([-8, 8]), np.array([-12, 12]), np.array([0, 1, 2, 3])]
    boundary_n = (1,)
    y_n = (0,1)
    batch_size = (80, 120, 11)
    batch_size_test = (100, 100, 4)
    boundary_batch_size = 11*17*20
    boundary_batch_size_test = 11*17*27
    boundary_weight = 10

    n_steps = 30000
    n_hidden, n_layers = 64, 4 # 64, 4
    point = np.array([0])
    A, args = PlaneActiveSchedulerND, (point, [0,1])
    width = 0.4
    subdomain_ws = get_subdomain_ws(subdomain_xs, width)
    run_FBPINN()
elif name=="HeatLongTime":
    P = HeatLongTime()
    subdomain_xs = [np.array([0, 1]), np.array([0, 1]), np.array([0, 25, 50, 75, 100])]
    boundary_n = (1,)
    y_n = (0,1)
    batch_size = (16, 16, 16)
    batch_size_test = (16, 16, 7)
    boundary_batch_size = 1024
    boundary_batch_size_test = 1024
    boundary_weight = 100

    n_steps = 10000
    n_hidden, n_layers = 64, 4
    A, args = AllActiveSchedulerND, ()
    width = 0.6
    subdomain_ws = get_subdomain_ws(subdomain_xs, width)
    run_FBPINN()
elif name=="HeatDarcy":
    P = HeatDarcy()
    subdomain_xs = [np.array([0, 1]), np.array([0, 1]), np.array([0, 1, 2, 3, 4, 5])]
    boundary_n = (1,)
    y_n = (0,1)
    batch_size = (16, 16, 16)
    batch_size_test = (64, 64, 5)
    boundary_batch_size = -1
    boundary_batch_size_test = -1
    boundary_weight = -1

    n_steps = 10000
    n_hidden, n_layers = 64, 4
    A, args = AllActiveSchedulerND, ()
    width = 0.6
    subdomain_ws = get_subdomain_ws(subdomain_xs, width)
    run_FBPINN()