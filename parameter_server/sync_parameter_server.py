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
parser.add_argument("--backups", default=0, type=int,
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

    def set_weights(self, weights):
        return self.net.variables.set_flat(weights)


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
        loss = self.net.compute_loss(test_xs, test_ys)
        tic = time.time()
        gradients = self.net.compute_gradients(xs, ys)
        toc = time.time()
        print("Worker {} | Iteration {} | Time {} | Accuracy is {} | Loss is {}".format(self.worker_index, self.curritr, toc - tic, accuracy, loss))
        self.curritr = self.curritr + 1
        return gradients

    def getWorkerIndex(self):
        return self.worker_index


if __name__ == "__main__":
    args = parser.parse_args()
    print("redis_address: ", args.redis_address)
    ray.init(redis_address=args.redis_address)

    # Create a parameter server.
    net = model.SimpleCNN()
    # net.load_model()

    ps = ParameterServer.remote(1e-4 * args.num_workers)
    set_weight = ps.set_weights.remote(net.variables.get_flat())
    wait_set_weight = ray.get(set_weight)

    # Create workers.
    workers = [Worker.remote(worker_index)
               for worker_index in range(args.num_workers)]

    # Download MNIST.
    mnist = model.download_mnist_retry()

    i = 1
    backups = args.backups #no. of stragglers, we will ignore results from them
    
    # current_weights = ps.get_weights.remote()
    current_weights = net.variables.get_flat()

    k = args.num_workers-backups

    bid_price = [0.488, 0.668]

    # assume the spot price is between 0.2 and 1
    epoch = 0
    while i<=1000:
        accs = []
        losses = []
        #spot_price = np.random.uniform(low=0.2, high=1.0)
        spot_price = np.random.normal(loc=0.6, scale=0.175)
        if spot_price <= bid_price[0]:
            k = 8
        elif spot_price <= bid_price[-1]:
            k = 4
        else:
            k = 0
        
        tic = time.time()

        fobj_to_workerID_dict = {} #mapping between remotefns to worker_ids
        compute_tasks = []

        for worker_id in range(0,args.num_workers):
            worker = workers[worker_id]
            remotefn = worker.compute_gradients.remote(current_weights)
            compute_tasks.append(remotefn)
            fobj_to_workerID_dict[remotefn] = worker_id

        if k != 0:
            fast_function_ids, straggler_function_ids  = ray.wait(compute_tasks, num_returns=k)
            fast_gradients = [ray.get(fast_id) for fast_id in fast_function_ids]

            current_weights = ps.apply_gradients.remote(*fast_gradients)

            # Evaluate the current model.
            net.variables.set_flat(ray.get(current_weights))
            toc = time.time()
            test_xs, test_ys = mnist.test.next_batch(1000)
            accuracy = net.compute_accuracy(test_xs, test_ys)
            accs.append(accuracy)
            loss = net.compute_loss(test_xs, test_ys)
            losses.append(loss)

            #net.save_model(i)

            fast_worker_IDs = [fobj_to_workerID_dict[fast_id] for fast_id in fast_function_ids]
            
            print("Iteration {} | Time {} | Accuracy is {} | Loss is {} | Fast workers {} | Bid price {} | Spot price {}".format(i, toc-tic, accuracy, loss, fast_worker_IDs, bid_price, spot_price)) 
            if i % 120 == 0:
                print("Epoch {} | Epoch accuracy is {} | Epoch loss is {}"
                    .format(i / 1200, np.asarray(accs).mean(), np.asarray(losses).mean()))
                accs = []
                losses = []
        else:
            print("Wait 0 work this iteration. Spot price {}".format(spot_price))

        i += 1 #next iteration

        fast_function_ids, straggler_function_ids  = ray.wait(compute_tasks, num_returns=args.num_workers)

