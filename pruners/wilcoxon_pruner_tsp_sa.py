import math
from typing import NamedTuple

import numpy as np
from numpy.linalg import norm
import optuna


class SAOptions(NamedTuple):
    max_iter: int = 1000
    T0: float = 1.0
    alpha: float = 1.0
    patience: int = 300


def simulated_annealing(vertices, initial_idxs, options: SAOptions):

    def temperature(t: float):
        # t: 0 ... 1
        return options.T0 * (1 - t) ** options.alpha

    idxs = initial_idxs.copy()
    N = len(vertices)
    assert len(idxs) == N

    cost = sum([norm(vertices[idxs[i]] - vertices[idxs[(i + 1) % N]]) for i in range(N)])
    best_idxs = idxs.copy()
    best_cost = cost

    remaining_patience = options.patience
    np.random.seed(11111)

    for iter in range(options.max_iter):
        i = np.random.randint(0, N)
        j = (i + 2 + np.random.randint(0, N - 3)) % N
        i, j = min(i, j), max(i, j)
        delta_cost = (
            -norm(vertices[idxs[(i + 1) % N]] - vertices[idxs[i]])
            - norm(vertices[idxs[j]] - vertices[idxs[(j + 1) % N]])
            + norm(vertices[idxs[i]] - vertices[idxs[j]])
            + norm(vertices[idxs[(i + 1) % N]] - vertices[idxs[(j + 1) % N]])
        )
        temp = temperature(iter / options.max_iter)
        if np.random.rand() < math.exp(-delta_cost / temp):
            cost += delta_cost
            idxs[i + 1 : j + 1] = idxs[i + 1 : j + 1][::-1]
            if cost < best_cost:
                best_idxs[:] = idxs
                best_cost = cost

        if cost >= best_cost:
            remaining_patience -= 1
            if remaining_patience == 0:
                idxs[:] = best_idxs
                cost = best_cost
                remaining_patience = options.patience

    return best_idxs


def make_dataset(num_vertex, num_problem, seed):
    rng = np.random.default_rng(seed=seed)
    dataset = []
    for _ in range(num_problem):
        dataset.append(
            {
                "vertices": rng.random((num_vertex, 2)),
                "idxs": rng.permutation(num_vertex),
            }
        )
    return dataset


N_DATAPOINTS, N_TRIALS = 20, 100
dataset = make_dataset(200, N_DATAPOINTS, seed=33333)
rng = np.random.default_rng(seed=44444)
count = 0


def objective(trial):
    global count
    patience = trial.suggest_int("patience", 10, 1000, log=True)
    T0 = trial.suggest_float("T0", 0.1, 10.0, log=True)
    alpha = trial.suggest_float("alpha", 1.1, 10.0, log=True)
    options = SAOptions(max_iter=10000, patience=patience, T0=T0, alpha=alpha)
    ordering = rng.permutation(range(len(dataset)))
    results = []
    for i in ordering:
        count += 1
        d = dataset[i]
        result_idxs = simulated_annealing(d["vertices"], d["idxs"], options)
        result_cost = 0.0
        n = len(d["vertices"])
        for j in range(n):
            result_cost += norm(
                d["vertices"][result_idxs[j]] - d["vertices"][result_idxs[(j + 1) % n]]
            )
        results.append(result_cost)

        trial.report(result_cost, i)
        if trial.should_prune():
            sum(results) / len(results)  # An advanced technique
            # raise optuna.TrialPruned()

    return sum(results) / len(results)


if __name__ == "__main__":
    sampler = optuna.samplers.TPESampler(seed=55555)
    pruner = optuna.pruners.WilcoxonPruner(p_threshold=0.05)
    study = optuna.create_study(direction="minimize", sampler=sampler, pruner=pruner)
    study.enqueue_trial({"patience": 300, "T0": 1.0, "alpha": 1.8})  # default params
    study.optimize(objective, n_trials=N_TRIALS)
    print(f"The number of trials: {len(study.trials)}")
    print(f"Best value: {study.best_value} (params: {study.best_params})")
    print(f"Number of evaluations: {count} / {N_DATAPOINTS * N_TRIALS}")
