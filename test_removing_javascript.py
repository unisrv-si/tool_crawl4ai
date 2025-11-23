from simple_web_crawl import remove_javascript_void_zero

md = """
  * 受付時間
月～土曜日 9～17時  
（日曜日・祝日・年末年始を除く） 
[ 0120-995-113 （スキップ番号：61） ](javascript:void\(0\);)
自動音声が流れます。スキップ番号を入力してください。
音声案内の途中でもボタン操作が可能です。
"""


if __name__ == "__main__":
    print("Before:")
    print(md)
    print("\nAfter:")
    modified_md = remove_javascript_void_zero(md)
    print(modified_md)




