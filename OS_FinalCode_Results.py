import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("border_simulation.csv")

# Distribution of the results
result = df['result'].value_counts()
plt.figure()
result.plot(kind='bar')
plt.title('Result Distribution')
plt.xlabel('Result')
plt.ylabel('Count')
plt.show()

# Legal vs illegal
entry = df['entry_type'].value_counts()
plt.figure()
entry.plot(kind='bar')
plt.title('Legal vs Illegal')
plt.xlabel('Type')
plt.ylabel('Count')
plt.show()

# Results by method (accepted, caught or rejected)
method = df.groupby(['method', 'result']).size().unstack(fill_value=0)
plt.figure()
method.plot(kind='bar')
plt.title('Results by Method')
plt.xlabel('Method')
plt.ylabel('Count')
plt.xticks(rotation=45)
plt.show()


# Results by water, air and land
type = df.groupby(['medium', 'result']).size().unstack(fill_value=0)
plt.figure()
type.plot(kind='bar')
plt.title('Results by water, air and land')
plt.xlabel('Type')
plt.ylabel('Count')
plt.show()