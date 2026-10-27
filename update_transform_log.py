import pandas as pd
import os
import sys

def update_transform_log(df, name, action, destination):
    '''
    update `transform_log.csv` \
    
    df: the pandas DataFrame to be analyzed (dtype: DataFrame) \
    name: the source or name of the DataFrame (dtype: str) \
    action: the type of transformation (dtype: str) \
    destination: the save point if there is one (dtype: str)
    
    '''
    
    rows = df.shape[0]
    cols = df.shape[1]
    column_names = list(df.columns)
    script_name = os.path.basename(sys.argv[0])
    cur_time = pd.Timestamp.now()
    transform_cols = ['name', 'action', 'script_name', 
                      'num_of_cols', 'num_of_rows', 'feature_names', 
                      'execution_time', 'destination']
    df_final = pd.DataFrame([[name,action,script_name,cols,rows,
                              column_names,cur_time,destination]], 
                            columns = transform_cols)
    
    if not os.path.isfile('transform_log.csv'):
        print('Initalize transforma_log.csv')
        df_final.to_csv('transform_log.csv', mode='a', index=False, header=True)
        print('Saved row in transform_log.csv: ', df_final)
    else:
        df_final.to_csv('transform_log.csv', mode='a', index=False, header=False)
        print('Saved row in transform_log.csv: ', df_final)
    
    