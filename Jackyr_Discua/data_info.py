import pandas as pd

dataframe = pd.read_csv('lmfdb_gps_transitive_0625_1931.csv')

for row in dataframe.columns:
    

print(dataframe)