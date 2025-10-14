import pandas as pd

containers = pd.read_csv('container_capacity.csv')
c = containers[containers['id']==1].iloc[0]  # f_k

print(f"容器: {c['name']} ({c['width']}x{c['depth']})")
print(f"max_stack: {c['max_stack']}")
print(f"1容器の底面積: {c['width'] * c['depth']:,} mm²")

print("\n=== 段積み統合の計算 ===")

# V065104703: 18容器
existing = 18
print(f"\n既存: V065104703 {existing}容器")
existing_stacks = (existing + c['max_stack'] - 1) // c['max_stack']
print(f"  配置数: {existing_stacks}")
print(f"  底面積: {existing_stacks * c['width'] * c['depth']:,} mm²")

# V053904703: 3容器を追加
print(f"\n追加1: V053904703 3容器")
total1 = existing + 3
new_stacks1 = (total1 + c['max_stack'] - 1) // c['max_stack']
additional1 = new_stacks1 - existing_stacks
print(f"  合計容器数: {total1}")
print(f"  新配置数: {new_stacks1}")
print(f"  追加配置: {additional1}")
print(f"  追加底面積: {additional1 * c['width'] * c['depth']:,} mm²")

# V065103703: 1容器をさらに追加
print(f"\n追加2: V065103703 1容器")
total2 = total1 + 1
new_stacks2 = (total2 + c['max_stack'] - 1) // c['max_stack']
additional2 = new_stacks2 - new_stacks1
print(f"  合計容器数: {total2}")
print(f"  新配置数: {new_stacks2}")
print(f"  追加配置: {additional2}")
print(f"  追加底面積: {additional2 * c['width'] * c['depth']:,} mm²")

print("\n=== 問題 ===")
print("V065103703を追加する際、既存の容器数は18容器（V065104703）のみを")
print("カウントすべきですが、V053904703の3容器も含めてカウントしています。")
print("\n正しい計算:")
print(f"  V065104703: 18容器 → 9配置")
print(f"  V065103703: 1容器を追加 → 合計19容器 → 10配置")
print(f"  追加配置: 10 - 9 = 1配置")
print(f"  追加底面積: {1 * c['width'] * c['depth']:,} mm²")
