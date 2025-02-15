# dispy
Module for working with DIS

```python
import dispy

fpath = '/path/to/extract.csv'
dis = dispy.DIS()
dis.load_extract(fpath)

# -- results by RO and OU by year
dis.get_aggregate_results('EG.3.2-25')
```
