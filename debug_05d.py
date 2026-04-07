#!/usr/bin/env python3
def hex_to_decimal_with_sign(value, bit_width):
    """
    将数值字符串转换为带符号的十进制数
    :param value: 数值字符串（可能是十进制、十六进制或带符号的）
    :param bit_width: 数据位宽
    :return: 带符号的十进制数
    """
    try:
        # 移除可能的前缀和格式化字符
        # 只移除前缀和后缀的字符，避免删除数值中的字符
        clean_value = str(value).strip().lower().replace("'", "")
        print(f"原始值: \"{value}\", 处理后: \"{clean_value}\"")

        if clean_value.endswith('h'):
            clean_value = clean_value[:-1]
            print(f"移除h后缀: \"{clean_value}\"")
        elif clean_value.endswith('d'):
            clean_value = clean_value[:-1]
            print(f"移除d后缀: \"{clean_value}\"")

        if clean_value.startswith('0x'):
            clean_value = clean_value[2:]
            print(f"移除0x前缀: \"{clean_value}\"")

        if not clean_value:
            return 0

        if clean_value.startswith('-'):
            try:
                return int(clean_value)
            except:
                pass

        if bit_width == 1:
            try:
                return int(clean_value, 16) if clean_value else 0
            except:
                return int(clean_value) if clean_value else 0

        is_hex = False

        if any(c in 'abcdef' for c in clean_value):
            is_hex = True
            print('包含字母字符，设置为十六进制')
        elif len(clean_value) == 3 and (any(c in 'abcdef' for c in clean_value) or 'f' in clean_value):
            is_hex = True
        elif len(clean_value) > 1 and (clean_value[0] == '0' and len(clean_value) == 3 or
                                       clean_value == 'fff' or clean_value == 'ffd' or clean_value == 'ffe'):
            is_hex = True

        print(f'is_hex: {is_hex}, 最终值: "{clean_value}"')

        if is_hex:
            try:
                unsigned_val = int(clean_value, 16)
                print(f'十六进制转换: {unsigned_val}')

                if bit_width > 0:
                    sign_bit = 1 << (bit_width - 1)
                    if unsigned_val & sign_bit:
                        unsigned_val -= (1 << bit_width)
                        print(f'符号扩展后: {unsigned_val}')

                return unsigned_val
            except Exception as e:
                print(f'十六进制转换失败: {e}')

        try:
            return int(clean_value)
        except Exception as e:
            print(f'十进制转换失败: {e}')
            return 0

    except Exception as e:
        print(f'错误: {e}')
        return 0

# 测试'05d'
result = hex_to_decimal_with_sign('05d', 12)
print(f'最终结果: {result}')
