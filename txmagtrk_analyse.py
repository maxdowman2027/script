import pandas as pd
import matplotlib.pyplot as plt
import os
import re
import numpy as np
import traceback
from matplotlib.backends.backend_pdf import PdfPages 
import gc  
from itertools import product

AMPLITUDE_COL = 'amplitude'
STYLE_MAP = {
    # trk_en=0（参考数据）：amp0=实线圆 | amp1=虚线三角
    (0, 0): {
        'linestyle': '-', 'marker': 'o', 'linewidth': 2,
        'alpha': 0.9, 'markerfacecolor': 'none', 'markeredgewidth': 2,
        'label_suffix': 'magtrack off'
    },
    (0, 1): {
        'linestyle': '--', 'marker': '^', 'linewidth': 2,
        'alpha': 0.9, 'markerfacecolor': 'none', 'markeredgewidth': 2,
        'label_suffix': 'magtrack on(Instruments)'
    },
    # trk_en=1（主数据）：amp0=实线方 | amp1=虚线菱形
    (1, 0): {
        'linestyle': '-', 'marker': 's', 'linewidth': 2,
        'alpha': 0.9, 'markerfacecolor': 'none', 'markeredgewidth': 2,
        'label_suffix': 'magtrack on(E22 chip)'
    },
    (1, 1): {
        'linestyle': '--', 'marker': 'D', 'linewidth': 2,
        'alpha': 0.9, 'markerfacecolor': 'none', 'markeredgewidth': 2,
        'label_suffix': 'magtrack on(E22 chip and Instruments)'
    }
}

CONFIG = {
    # 自定义参数列名（改为你的CSV中实际列名，如'bandwidth'/'modulation'/'gain'等）
    'CUSTOM_PARAM_COL': 'dc_comp_en',
    # 是否强制要求自定义参数列（False则无该列时降级为仅test_rate着色）
    'REQUIRE_CUSTOM_PARAM': False,
    # 基础颜色池（可扩展，保证颜色区分度）
    'BASE_COLORS': [
        '#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF', "#FF007700", 
        '#800000', '#008000', '#000080', '#808000', '#800080', '#008080', "#00FFF744", 
        '#FF8000', '#FF0080', '#80FF00', '#00FF80', '#8000FF', '#0080FF', "#FF620026"
    ],

    # EVM相关参数（新增evm_nss1）
    'EVM_COLS': ['evm', 'evm_nss1'],  # 要绘图的EVM类参数
    'REQUIRE_EVM_NSS1': False  # 是否强制要求evm_nss1列（False则缺失时仅画evm）
}



def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]


def read_and_preprocess_csv(csv_file_path, encoding='utf-8'):
    print(f"\n📋 处理文件：{os.path.basename(csv_file_path)}")
    custom_param_col = CONFIG['CUSTOM_PARAM_COL']
    evm_cols = CONFIG['EVM_COLS']
    try:
        with open(csv_file_path, 'r', encoding=encoding, errors='ignore') as f:
            header_line = ''
            while not header_line:
                header_line = f.readline().strip()
            header_cols = [col.strip().lower() for col in header_line.split(',')]
            print(f"   📌 CSV关键列：{[c for c in header_cols if c in ['trk_en', 'amplitude', 'test_rate', 'numsymbols', 'win_len', 'start_point', 'chn_ofst',custom_param_col]  + evm_cols]}")
    except Exception as e:
        print(f"❌ 读取表头失败：{e}")
        return None, None

    pd_version = tuple(map(int, pd.__version__.split('.')[:2]))
    read_kwargs = {'index_col': False, 'encoding': encoding}
    if pd_version >= (1, 3):
        read_kwargs['on_bad_lines'] = 'warn'
    else:
        read_kwargs['warn_bad_lines'] = True
        read_kwargs['error_bad_lines'] = False

    try:
        df = pd.read_csv(csv_file_path,** read_kwargs)
        df.columns = [col.strip().lower() for col in df.columns]
    except Exception as e:
        print(f"❌ 读取CSV失败：{e}")
        return None, None

    required_cols = ['trk_en', 'start_point', 'win_len', 'chn_ofst', 'evm', 'test_power', 'test_rate', 'numsymbols', AMPLITUDE_COL.lower(), 'ru_size']
    if CONFIG['REQUIRE_EVM_NSS1']:
        required_cols.append('evm_nss1')
    if CONFIG['REQUIRE_CUSTOM_PARAM']:
        required_cols.append(custom_param_col.lower())
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"❌ 缺失必要列（含chn_ofst）：{missing_cols}，无法按四参数分组")
        return None, None

    numeric_cols = ['trk_en', 'start_point', 'win_len', 'chn_ofst', 'test_power', 'numsymbols', AMPLITUDE_COL.lower()] + evm_cols
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=[col])
    df['test_rate'] = df['test_rate'].astype(str).str.strip()
    if custom_param_col.lower() in df.columns :
        df[custom_param_col.lower()] = df[custom_param_col.lower()].astype(str).str.strip()
    df.rename(columns={AMPLITUDE_COL.lower(): 'amplitude'}, inplace=True)

    trk0_df = df[df['trk_en'] == 0].copy()
    trk1_df = df[df['trk_en'] == 1].copy()
    group_cols = ['start_point', 'win_len', 'chn_ofst', 'numsymbols', 'ru_size', 'test_rate',custom_param_col.lower(), 'amplitude', 'trk_en', 'test_power']
    group_cols = [col for col in group_cols if col in trk0_df.columns]
    trk0_agg = None
    trk1_agg = None
    for evm_col in evm_cols:
        trk0_agg_single = trk0_df.groupby(group_cols)[evm_col].mean().reset_index()
        if trk0_agg is None:
            trk0_agg = trk0_agg_single  # 第一次聚合，直接赋值
        else:
            trk0_agg = pd.merge(trk0_agg, trk0_agg_single, on=group_cols, how='outer')

        trk1_agg_single = trk1_df.groupby(group_cols)[evm_col].mean().reset_index()
        if trk1_agg is None:
            trk1_agg = trk1_agg_single  # 第一次聚合，直接赋值
        else:
            trk1_agg = pd.merge(trk1_agg, trk1_agg_single, on=group_cols, how='outer')        
    
    trk0_df = trk0_agg     
    trk1_df = trk1_agg   
    print(f"✅ 预处理完成：")
    print(f"   - trk_en=0（参考）：{len(trk0_df)}行 | chn_ofst值：{sorted(trk0_df['chn_ofst'].unique()) if len(trk0_df) > 0 else []}")
    print(f"   - trk_en=1（主数据）：{len(trk1_df)}行 | chn_ofst值：{sorted(trk1_df['chn_ofst'].unique()) if len(trk1_df) > 0 else []}")
    print(f"   - 可用EVM列：{[col for col in evm_cols if col in df.columns]}")
    return trk0_df, trk1_df

def plot_single_evm_metric(ax, data, evm_col, test_rates, custom_params, custom_param_col, color_map, trk_en, style_map):
    """绘制单个EVM指标（evm/evm_nss1）的曲线"""
    for test_rate in test_rates:
        for custom_param in custom_params:
            # 筛选当前test_rate + 自定义参数的数据
            rate_param_data = data[
                (data['test_rate'] == test_rate) & 
                (data[custom_param_col] == custom_param)
            ].copy()
            
            for amp in [0, 1]:
                amp_data = rate_param_data[rate_param_data['amplitude'] == amp].sort_values('test_power').copy()
                if len(amp_data) == 0:
                    continue
                
                # 获取样式和颜色
                style = style_map[(trk_en, amp)]
                combo = (test_rate, custom_param)
                color = color_map[combo]
                
                # 绘制线条（使用当前EVM列）
                ax.plot(
                    amp_data['test_power'], amp_data[evm_col],
                    color=color,
                    linestyle=style['linestyle'],
                    marker=style['marker'],
                    linewidth=style['linewidth'],
                    alpha=style['alpha'],
                    markerfacecolor=style['markerfacecolor'],
                    markeredgewidth=style['markeredgewidth'],
                    markersize=6,
                    label=f"{style['label_suffix']} | test_rate={test_rate} | {CONFIG['CUSTOM_PARAM_COL']}={custom_param}"
                )

def get_color_for_combination(comb, color_pool):
    """为(test_rate, 自定义参数)组合生成唯一颜色"""
    if comb[1] != 0 :
        comb_index = int(comb[1])
    elif comb[0] == 0 :
        comb_index = 3
    else :
        comb_index = hash(comb) % len(color_pool)
    print(f"------------------comb:{comb[0]  ,comb[1]}-------------------------------------------")
    return color_pool[comb_index]

def generate_and_save_figs(trk0_df, trk1_df, pdf_save_path):
    """优化：生成一个图表就保存一个，不缓存所有fig，大幅降低内存占用"""
    # 先删除已有PDF（强制覆盖）
    if os.path.exists(pdf_save_path):
        try:
            os.remove(pdf_save_path)
            print(f"🗑️  已删除同名PDF文件：{pdf_save_path}")
        except Exception as e:
            print(f"❌ 删除同名PDF失败：{e}")
            return False

    if len(trk1_df) == 0:
        print("🚫 无trk_en=1的有效数据，无法生成图表")
        return False
    total_fig_count = 0 
    custom_param_col = CONFIG['CUSTOM_PARAM_COL'].lower()
    # 创建PDF对象（持续写入，不缓存所有fig）
    pdf = PdfPages(pdf_save_path)
    test_rates = sorted(trk1_df['test_rate'].unique(), key=natural_sort_key)

    custom_params = sorted(trk1_df[custom_param_col].unique(), key=natural_sort_key)
    evm_cols = [col for col in CONFIG['EVM_COLS'] if col in trk1_df.columns]  
    if len(trk0_df) > 0:
        test_rates = sorted(list(set(test_rates) | set(trk0_df['test_rate'].unique())), key=natural_sort_key)
        custom_params = sorted(list(set(custom_params) | set(trk0_df[custom_param_col].unique())), key=natural_sort_key)
    # 生成颜色映射：(test_rate, 自定义参数) → 唯一颜色
    color_pool = CONFIG['BASE_COLORS']
    combos = list(product(test_rates, custom_params))
    color_map = {combo: get_color_for_combination(combo, color_pool) for combo in combos}

    trk1_groups = sorted(
        trk1_df.groupby(['start_point', 'win_len', 'numsymbols', 'chn_ofst', 'ru_size']).groups.keys(),
        key=lambda x: (x[0], x[1], x[2], x[3], x[4])
    )

    chn_ofst_values = sorted(list(set([g[3] for g in trk1_groups])))
    print(f"\n📊 trk_en=1分组概览：")
    print(f"   ├─ 总分组数（五参数组合）：{len(trk1_groups)}")
    print(f"   └─ chn_ofst值分布：{chn_ofst_values}")

    # 核心优化：逐个生成图表并写入PDF，生成一个释放一个
    for idx, (start_point, win_len, numsymbols, chn_ofst, ru_size) in enumerate(trk1_groups, 1):
        trk1_data = trk1_df[
            (trk1_df['start_point'] == start_point) &
            (trk1_df['win_len'] == win_len) &
            (trk1_df['numsymbols'] == numsymbols) &
            (trk1_df['chn_ofst'] == chn_ofst) &
            (trk1_df['ru_size'] == ru_size)
        ].copy()
        if len(trk1_data) == 0:
            continue

        trk0_ref_data = trk0_df[trk0_df['numsymbols'] == numsymbols].copy() if len(trk0_df) > 0 else pd.DataFrame()
        has_trk0_ref = len(trk0_ref_data) > 0

        for evm_col in evm_cols:
            total_fig_count += 1
            print(f"\n🔧 生成图表 [{total_fig_count}]：")
            print(f"   ├─ 五参数组合：start_point={start_point} | win_len={win_len} | numsymbols={numsymbols} | chn_ofst={chn_ofst} | ru_size={ru_size}")
            print(f"   ├─ EVM指标：{evm_col.upper()}")
            print(f"   └─ trk_en=0参考数据（同={numsymbols}）：{'有' if has_trk0_ref else '无'}")

            # 创建图表（减小尺寸，内存优化）
            fig, ax = plt.subplots(figsize=(10, 6))
            # 标题增强：明确标注EVM指标类型
            title = (
                f"{evm_col.upper()}:trk_en=1 vs trk_en=0\n"
                f"start_point={start_point} | win_len={win_len} | numsymbols={numsymbols} | chn_ofst={chn_ofst} | ru_size={ru_size}\n"
            )
            ax.set_title(title, fontsize=12, fontweight='bold', pad=15, color='#2c3e50')
            ax.set_xlabel('Test Power', fontsize=10, fontweight='bold')
            ax.set_ylabel(evm_col.upper(), fontsize=10, fontweight='bold')  # Y轴标注当前EVM指标
            ax.grid(True, alpha=0.3, linestyle='-')

            # 绘制trk_en=1主数据（当前EVM指标）
            plot_single_evm_metric(ax, trk1_data, evm_col, test_rates, custom_params, custom_param_col, color_map, 1, STYLE_MAP)

            # 绘制trk_en=0参考数据（当前EVM指标）
            if has_trk0_ref:
                plot_single_evm_metric(ax, trk0_ref_data, evm_col, test_rates, custom_params, custom_param_col, color_map, 0, STYLE_MAP)
            else:
                ax.plot([], [], color='gray', linestyle='-', marker='o', label=f"trk_en=0（参考）| 无同pklen数据")

            # 优化图例
            ax.legend(
                loc='upper left', 
                bbox_to_anchor=(1.02, 1), 
                ncol=1, 
                fontsize=7,
                frameon=True,
                shadow=True
            )
            plt.tight_layout()

            # 写入PDF并释放内存
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)
            gc.collect()
            print(f"✅ {evm_col.upper()}图表写入PDF并释放内存：五参数={start_point}-{win_len}-{numsymbols}-{chn_ofst}-{ru_size}")

    # 关闭PDF文件
    pdf.close()
    print(f"\n🎉 PDF保存成功（已覆盖同名文件）：{pdf_save_path}")
    print(f"📄 PDF总页数（所有EVM指标+四参数组合）：{total_fig_count}")
    return True

def save_figs_to_pdf(fig_list, pdf_save_path):
    """保存图表到PDF（强制覆盖已存在的同名文件）"""
    if len(fig_list) == 0:
        print(f"🚫 无图表可保存：{pdf_save_path}")
        return False

    # 递归创建目录
    pdf_dir = os.path.dirname(pdf_save_path)
    if pdf_dir and not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir, exist_ok=True)
        print(f"📁 创建目录：{pdf_dir}")

    # ========== 核心修改：强制覆盖已存在的PDF文件 ==========
    if os.path.exists(pdf_save_path):
        try:
            os.remove(pdf_save_path)  # 删除已存在的文件
            print(f"🗑️  已删除同名PDF文件：{pdf_save_path}")
        except PermissionError:
            print(f"❌ 无法覆盖PDF文件（文件被占用）：{pdf_save_path}")
            return False
        except Exception as e:
            print(f"❌ 删除同名PDF失败：{e}")
            return False
    # ======================================================

    try:
        with PdfPages(pdf_save_path) as pdf:
            for fig in fig_list:
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)
        print(f"\n🎉 PDF保存成功（已覆盖同名文件）：{pdf_save_path}")
        print(f"📄 PDF总页数（四参数组合数）：{len(fig_list)}")
        return True
    except Exception as e:
        print(f"❌ 保存PDF失败：{e}")
        return False


def batch_process_csv(csv_dir, pdf_save_root_dir, recursive=True):
    csv_files = []
    for root, _, files in os.walk(csv_dir):
        for file in files:
            if file.lower().endswith('.csv'):
                csv_files.append(os.path.abspath(os.path.join(root, file)))
        if not recursive:
            break

    if len(csv_files) == 0:
        print("🚫 未找到CSV文件")
        return

    print(f"\n🔍 共找到{len(csv_files)}个CSV文件：")
    for i, f in enumerate(csv_files, 1):
        print(f"   {i}. {f}")

    for csv_file in csv_files:
        # 每次处理完一个CSV，强制回收内存
        gc.collect()
        trk0_df, trk1_df = read_and_preprocess_csv(csv_file)
        if trk1_df is None or len(trk1_df) == 0:
            print(f"⚠️ 跳过文件：{csv_file}（无trk_en=1数据或缺失chn_ofst）")
            continue

        # 创建保存目录
        if not os.path.exists(pdf_save_root_dir):
            os.makedirs(pdf_save_root_dir, exist_ok=True)
        
        # 生成PDF路径
        csv_basename = os.path.splitext(os.path.basename(csv_file))[0]
        pdf_save_path = os.path.join(pdf_save_root_dir, f"{csv_basename}.pdf")
        
        # 生成并保存图表（逐个写入，不缓存）
        generate_and_save_figs(trk0_df, trk1_df, pdf_save_path)
        
        # 处理完一个CSV，清空数据并回收内存
        del trk0_df, trk1_df
        gc.collect()

    print(f"\n✅ 所有CSV处理完成！PDF保存根目录：{pdf_save_path}")
    print(f"📌 关键说明：已优化内存占用，支持批量处理大量图表")


# ---------------------- 运行配置 ----------------------
if __name__ == "__main__":
    CSV_DIR = r"D:\users\gxu\txmagtrk\260317_fake_tb\2"          
    SAVE_ROOT_DIR = r"D:\users\gxu\txmagtrk\260317_fake_tb\2\result" 
    RECURSIVE_SEARCH = False     
    CONFIG['CUSTOM_PARAM_COL'] = 'start_mode'
    CONFIG['REQUIRE_CUSTOM_PARAM'] = False
    CONFIG['REQUIRE_EVM_NSS1'] = False
    try:
        gc.collect()
        batch_process_csv(CSV_DIR, SAVE_ROOT_DIR, RECURSIVE_SEARCH)
        print("\n🎉 所有文件处理完成！")
    except Exception as e:
        print(f"\n💥 程序异常：{e}")
        traceback.print_exc()