
import subprocess
import os

def run_fake_tb_para(ul_bw, ru_allocation, ru_allocation_index, apep_len, last_mpdu_len):
    script_path = "D:\\users\\gxu\\scripts\\fake_tb_para.py"

    # 创建临时修改版本的fake_tb_para.py
    temp_script_path = "D:\\users\\gxu\\scripts\\temp_fake_tb_para.py"

    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 替换相关参数
    content = content.replace("ul_bw = 1", f"ul_bw = {ul_bw}")
    content = content.replace("ru_allocation = 26", f"ru_allocation = {ru_allocation}")
    content = content.replace("ru_allocation_index = 16", f"ru_allocation_index = {ru_allocation_index}")
    content = content.replace("apep_len = 44", f"apep_len = {apep_len}")
    content = content.replace("last_mpdu_len = 40", f"last_mpdu_len = {last_mpdu_len}")

    with open(temp_script_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # 运行脚本
    result = subprocess.run(["python", temp_script_path], capture_output=True, text=True, cwd="D:\\users\\gxu\\scripts")

    return result.stdout

# 带宽对应关系：20M→0，40M→1，80M→2，160M→3
bandwidth_map = {
    20: 0,
    40: 1,
    80: 2,
    160: 3
}

# ru_allocation=26时的ru_allocation_index值需要根据带宽确定
# 我需要查看现有的case配置来了解
# 从之前查看的wifi_tx_test.py中可以看到，ru=26的情况通常使用的ru_allocation_index可能是9或其他值
# 让我查看一下其他case的249c寄存器值
# 例如case 0的reg_249c值是0x80094041 → ru_allocation_index位是第13-20位？
# 根据fake_tb_para.py中的代码：(ru_allocation_index << 13)

# 我将尝试几个可能的值
ru_allocation = 26

# 对于n_sym=16的情况
print("=== n_sym=16 ===")
for bandwidth in [20, 40, 80, 160]:
    ul_bw = bandwidth_map[bandwidth]
    apep_len = 21
    last_mpdu_len = 17
    # 对于不同带宽，ru_allocation_index可能不同
    # 20M时，可能是9（来自case0的0x80094041）
    ru_allocation_index = 9
    if ul_bw == 1:  #40M
        ru_allocation_index = 0x0d  # 来自case2的0x800d4000
    elif ul_bw == 2:  #80M
        ru_allocation_index = 0x0f  # 来自case6的0x800f5041
    elif ul_bw == 3:  #160M
        ru_allocation_index = 0x10  # 来自case7的0x80105041

    print(f"\n带宽 {bandwidth}M:")
    output = run_fake_tb_para(ul_bw, ru_allocation, ru_allocation_index, apep_len, last_mpdu_len)
    print(output)

# 对于n_sym=340的情况
print("\n=== n_sym=340 ===")
for bandwidth in [20, 40, 80, 160]:
    ul_bw = bandwidth_map[bandwidth]
    apep_len = 507
    last_mpdu_len = 503
    ru_allocation_index = 9
    if ul_bw == 1:
        ru_allocation_index = 0x0d
    elif ul_bw == 2:
        ru_allocation_index = 0x0f
    elif ul_bw == 3:
        ru_allocation_index = 0x10

    print(f"\n带宽 {bandwidth}M:")
    output = run_fake_tb_para(ul_bw, ru_allocation, ru_allocation_index, apep_len, last_mpdu_len)
    print(output)

# 清理临时文件
try:
    os.remove("D:\\users\\gxu\\scripts\\temp_fake_tb_para.py")
except:
    pass
