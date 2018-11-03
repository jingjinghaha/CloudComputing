from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import numpy as np
import time

import ray
import model

parser = argparse.ArgumentParser(description="Run the synchronous parameter "
                                             "server example.")
parser.add_argument("--num-workers", default=8, type=int,
                    help="The number of workers to use.")
parser.add_argument("--backups", default=2, type=int,
                    help="The no. of stragglers, we will ignore results from them.")
parser.add_argument("--redis-address", default=None, type=str,
                    help="The Redis address of the cluster.")


@ray.remote
class ParameterServer(object):
    def __init__(self, learning_rate):
        self.net = model.SimpleCNN(learning_rate=learning_rate)

    def apply_gradients(self, *gradients):
        self.net.apply_gradients(np.mean(gradients, axis=0))
        return self.net.variables.get_flat()

    def get_weights(self):
        return self.net.variables.get_flat()


@ray.remote
class Worker(object):
    def __init__(self, worker_index, batch_size=50, curritr=0):
        self.worker_index = worker_index
        self.batch_size = batch_size
        self.mnist = model.download_mnist_retry(seed=worker_index)
        self.net = model.SimpleCNN()
        self.curritr = curritr
        # self.currGradient = currGradient

    def compute_gradients(self, weights):
        self.net.variables.set_flat(weights)
        xs, ys = self.mnist.train.next_batch(self.batch_size)

        # Measure accuracy of the epoch
        test_xs, test_ys = self.mnist.test.next_batch(1000)
        accuracy = self.net.compute_accuracy(test_xs, test_ys)
        print("Worker {} : Iteration {} : accuracy is {}".format(self.worker_index, self.curritr, accuracy))
        self.curritr = self.curritr + 1
        tic = time.time()
        gradients = self.net.compute_gradients(xs, ys)
        toc = time.time()
        print("Time of computing gradients on worker {}: {}".format(self.worker_index, str(toc - tic)))
        return gradients

    def getWorkerIndex(self):
        return self.worker_index


if __name__ == "__main__":
    args = parser.parse_args()

    ray.init(redis_address=args.redis_address)

    # Create a parameter server.
    net = model.SimpleCNN()
    ps = ParameterServer.remote(1e-4 * args.num_workers)

    # Create workers.
    workers = [Worker.remote(worker_index)
               for worker_index in range(args.num_workers)]

    # Download MNIST.
    mnist = model.download_mnist_retry()

    iteration = 0
    backups = args.backups #no. of stragglers, we will ignore results from them
    print(args.num_workers, backups)
    current_weights = ps.get_weights.remote()

    
    k = args.num_workers-backups
    while iteration<=100:
        # Compute and apply gradients.
        # compute_tasks = [worker.compute_gradients.remote(current_weights) for worker in workers]
        fobj_to_workerID_dict = {} #mapping between remotefns to worker_ids
        compute_tasks = []
        
        for i in range(k):
            # tic = time.time()
            for worker_id in range(0,args.num_workers):
                worker = workers[worker_id]
                remotefn = worker.compute_gradients.remote(current_weights)
                compute_tasks.append(remotefn)
                fobj_to_workerID_dict[remotefn] = worker_id
            # toc = time.time()
            # print("Schedule task time: ", str(toc-tic))

        fast_function_ids, straggler_function_ids  = ray.wait(compute_tasks, num_returns=k)
        fast_worker_IDs = [fobj_to_workerID_dict[fastfn_id] for fastfn_id in fast_function_ids]
        straggler_worker_IDs = [fobj_to_workerID_dict[stragglerfn_id] for stragglerfn_id in straggler_function_ids]
        print(len(fast_function_ids), k, len(straggler_worker_IDs), fast_worker_IDs)
        fast_gradients = [ray.get(fast_id) for fast_id in fast_function_ids]

        current_weights = ps.apply_gradients.remote(*fast_gradients)
        net.variables.set_flat(ray.get(current_weights))
        test_xs, test_ys = mnist.test.next_batch(1000)
        accuracy = net.compute_accuracy(test_xs, test_ys)
        print("Iteration {} : accuracy is {}".format(iteration, accuracy))
        iteration += 1

        fast_function_ids, straggler_function_ids  = ray.wait(compute_tasks, num_returns=k*args.num_workers)
        print(len(straggler_function_ids))

