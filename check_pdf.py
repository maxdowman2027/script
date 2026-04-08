
import PyPDF2

def check_pdf_content(pdf_path):
    try:
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            print(f"PDF文件路径: {pdf_path}")
            print(f"总页数: {len(pdf_reader.pages)}")

            # 检查前几页的内容
            for i in range(min(3, len(pdf_reader.pages))):
                page = pdf_reader.pages[i]
                text = page.extract_text()

                if text:
                    print(f"\n第{i+1}页内容:")
                    print(text.strip())
                else:
                    print(f"\n第{i+1}页没有可提取的文本")

                print("-" * 50)

            print("\nPDF文件检查完成")
            return True
    except Exception as e:
        print(f"检查PDF文件时出错: {e}")
        return False

# 测试PDF文件
pdf_path = r"D:\chip_test\dev\xian_test\Xian-Esp-Test-Scripts\py_script_fpga_tx_wifi7\Log\wifi_tx\20260407\vht_ht\evm_comparison_by_tx_pwr.pdf"
check_pdf_content(pdf_path)
