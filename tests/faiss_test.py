import numpy as np
import faiss
import time
d = 512                           # dimension
nb = 100000                      # database size
nq = 100                       # nb of queries
np.random.seed(1234)             # make reproducible
xb = np.random.random((nb, d)).astype('float32')
xb[:, 0] += np.arange(nb) / 1000.
xq = np.random.random((nq, d)).astype('float32')
xq[:, 0] += np.arange(nq) / 1000.


start = time.time()
index = faiss.IndexFlatL2(d)   # build the index

print(index.is_trained)
index.add(xb)                  # add vectors to the index
print(index.ntotal)
print(index.is_trained)
print("Time to build:", time.time() - start)

for _ in range(10):
    start2 = time.time()
    index.add(xb[0].reshape((1, -1)))
    print("Time to add:", time.time() - start2)


k = 4                          # we want to see 4 nearest neighbors
D, I = index.search(xb[:5], k) # sanity check
print(I)
print(D)
print("actual search:")
start = time.time()
D, I = index.search(xq, k)     # actual search
print("Time to search batch:", time.time() - start)
print(I[:5])                   # neighbors of the 5 first queries
print(I[-5:])                  # neighbors of the 5 last queries

start = time.time()
faiss.write_index(index, 'index.faiss')
print('Time to write:', time.time() - start)


start = time.time()
print(index.ntotal)
index.remove_ids(np.asarray([0]))
print(index.ntotal)
print('Time to write:', time.time() - start)
