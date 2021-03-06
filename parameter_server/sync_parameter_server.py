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

    net = model.SimpleCNN()
    # net.load_model()

    # Create a parameter server.
    ps = ParameterServer.remote(1e-4 * args.num_workers)
    set_weight = ps.set_weights.remote(net.variables.get_flat())

    # Create workers.
    workers = [Worker.remote(worker_index)
               for worker_index in range(args.num_workers)]

    # Download MNIST.
    mnist = model.download_mnist_retry()
    backups = args.backups #no. of stragglers, we will ignore results from them
    
    current_weights = net.variables.get_flat()

    num_workers = 0

    distribution = 'normal'
    if distribution == 'uniform':
        bid_price_low1 = 0.5389
        bid_price_high1 = 0.7083
        bid_price_low2 = 0.4086
        bid_price_high2 = 0.7215
        bid_price_8 = 0.7353
    elif distribution == 'normal':
        bid_price_low1 = 0.566
        bid_price_high1 = 0.66
        bid_price_low2 = 0.488
        bid_price_high2 = 0.668
        bid_price_8 = 0.677

    i = 1
    epoch = 1
    running_time = 0.0
    epoch_time = 0.0
    cost = 0.0
    accs = []
    losses = []

    while i<=1000:
        if distribution == 'uniform':
            spot_price = np.random.uniform(low=0.2, high=1.0)
        elif distribution == 'normal':
            spot_price = np.random.normal(loc=0.6, scale=0.175)

        # if i <= 800:
        #     if spot_price <= bid_price_low1:
        #         num_workers = 4
        #     elif spot_price <= bid_price_high1:
        #         num_workers = 2
        #     else:
        #         num_workers = 0
        #         running_time += 3.841382
        #         continue
        # else:
        #     if spot_price <= bid_price_low2:
        #         num_workers = 8
        #     elif spot_price <= bid_price_high2:
        #         num_workers = 4
        #     else:
        #         num_workers = 0
        #         running_time += 4.015319
        #         continue

        # if spot_price <= bid_price_8:
        #     num_workers = 8
        # else:
        #     num_workers = 0
        #     running_time += 4.015319
        #     continue

        num_workers = 8

        # ps = ParameterServer.remote(1e-4 * num_workers)
        # set_weight = ps.set_weights.remote(net.variables.get_flat())

        tic = time.time()

        fobj_to_workerID_dict = {} #mapping between remotefns to worker_ids
        compute_tasks = []
        
        for worker_id in range(0, num_workers):
            worker = workers[worker_id]
            remotefn = worker.compute_gradients.remote(current_weights)
            compute_tasks.append(remotefn)
            fobj_to_workerID_dict[remotefn] = worker_id

        if num_workers != 0:
            fast_function_ids, straggler_function_ids  = ray.wait(compute_tasks, num_returns=num_workers)
            fast_gradients = [ray.get(fast_id) for fast_id in fast_function_ids]

            current_weights = ps.apply_gradients.remote(*fast_gradients)

            # Evaluate the current model.
            net.variables.set_flat(ray.get(current_weights))

            test_xs, test_ys = mnist.test.next_batch(1000)
            accuracy = net.compute_accuracy(test_xs, test_ys)
            accs.append(accuracy)
            loss = net.compute_loss(test_xs, test_ys)
            losses.append(loss)

            toc = time.time()
            iter_time = toc - tic
            running_time += iter_time
            cost += (spot_price * num_workers * iter_time / (60 * 60))

            #net.save_model(i)            
            print("Iteration {} | Time {} | Accuracy is {} | Loss is {} | Wait # workers {} | Cost {}".format(i, running_time, accuracy, loss, num_workers, cost)) 
            if i % 100 == 0:
                print("Epoch {} | Time {} | Epoch accuracy is {} | Epoch loss is {}"
                    .format(epoch, running_time, np.asarray(accs).mean(), np.asarray(losses).mean()))
                accs = []
                losses = []
                epoch += 1
        else:
            print("Wait 0 work this iteration. Spot price {}".format(spot_price))

        i += 1 #next iteration


