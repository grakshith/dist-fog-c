import numpy as np
import matplotlib.pyplot as plt
from sklearn import linear_model
import csv

dataset = csv.reader(open('plant_watering_system/dataset.csv', 'rb'), delimiter=',')
data = list(dataset)[1:13622]
res = np.array(data).astype('float')
X = res[:, 1:4]
Y = res[:, -1]
logreg = linear_model.LogisticRegression(C=1e5)
logreg.fit(X, Y)

if __name__ == '__main__':
    while True:
        try:
            X = raw_input()
            X = X.split(",")
            X = map(float, X)
            X = np.array(X).reshape(1, 3)
            print logreg.predict(X)
        except KeyboardInterrupt:
            exit(0)
