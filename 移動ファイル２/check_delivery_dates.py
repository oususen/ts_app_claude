import pandas as pd

orders = pd.read_csv('delivery_progress.csv')
print('納期の範囲:')
print(f'最小: {orders["delivery_date"].min()}')
print(f'最大: {orders["delivery_date"].max()}')
print(f'\n納期別件数:')
print(orders['delivery_date'].value_counts().sort_index())

print('\n\n積み残し製品の納期:')
print('\nV053104642:')
print(orders[orders['product_id']==4][['product_id', 'delivery_date', 'remaining_quantity']])

print('\nV065103703:')
print(orders[orders['product_id']==6][['product_id', 'delivery_date', 'remaining_quantity']])
