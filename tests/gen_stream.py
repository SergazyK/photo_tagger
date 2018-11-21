from multiprocessing import Pool, Queue, Process
import random
import time

def fast_gen(gen, jobs, num_workers = 10, qsize = 128):
	tasks = Queue()
	queue = Queue()
	
	def worker(input, output):
		for job in iter(input.get, 'STOP'):
			cur_gen = gen(job)
			for batch in cur_gen:
				output.put(batch)

	for it in range(num_workers):
		Process(target=worker, args=(tasks, queue)).start()

	while True:
		while tasks.qsize() < qsize:
			tasks.put(random.choice(jobs))

		if queue.qsize() == 0:
			time.sleep(1.0)
		else:
			print(queue.qsize())
			yield queue.get()



def gen(job_id):
	for _ in range(100):
		time.sleep(1)
		yield 100**5

start = time.time()
for _ in fast_gen(gen, range(100)):
	time.sleep(0.1)

print(time.time() - start)