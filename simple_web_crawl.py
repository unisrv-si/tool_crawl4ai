# Case01: Crawl a website and save the result to a file
import asyncio
import os
import re
import time
from crawl4ai import CrawlerRunConfig, AsyncWebCrawler
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from util import url2fname
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv
from table_unspanner import TableUnspanner

load_dotenv()

# crawler = AsyncWebCrawler()

config = CrawlerRunConfig(
    # Content thresholds
    # word_count_threshold=10,        # Minimum words per block
    # remove_overlay_elements=True,
    remove_overlay_elements=False,
    scraping_strategy=LXMLWebScrapingStrategy(),  # Faster alternative to default BeautifulSoup
    # js_code=[
    #     "document.getElementById('check-in-box')?.click();",
    # ],
    # Exclude elements such as #header like <div id="header">...</div>
    # tepco-ep pc用のselectorは除外しsp(スマホ)用のselectorは残す
    excluded_selector = os.getenv("EXCLUDE_SELECTOR", "#header, .header, #footer, .footer"),
    # Tag exclusions
    excluded_tags=['form', 'header', 'breadcrumbs' , 'footer', 'nav'],
    process_iframes=True,
    # Link filtering
    exclude_external_links=False,    
    exclude_social_media_links=False,
    # Block entire domains
    # exclude_domains=["adtrackers.com", "spammynews.org"],    
    exclude_social_media_domains=["facebook.com", "x.com"],

    # Media filtering
    exclude_external_images=False,
)



def fix_multiline_table_cells(markdown_text: str) -> str:
    """ Fix multiline table cells by merging lines that are part of the same cell.
    Args:
        markdown_text: The markdown content as a string.
    Returns:
        The modified markdown content with multiline cells merged."""
    lines = markdown_text.split('\n')
    result_lines = []
    i = 0
    
    while i < len(lines):
        current_line = lines[i]
        
        # If this is a table row (contains |)
        if '|' in current_line and current_line.strip():
            # Collect all subsequent lines that don't start with | or contain |
            collected_lines = [current_line.rstrip()]
            j = i + 1
            
            while (j < len(lines) and 
                    lines[j].strip() and
                    not lines[j].lstrip().startswith('|') and
                    not lines[j].lstrip().startswith('-') and
                    not lines[j].lstrip().startswith('#') and
                    '|' not in lines[j]):
                collected_lines.append(lines[j].strip())
                j += 1
            
            # Join with <br> if we have multiple lines
            if len(collected_lines) > 1:
                merged_line = '<br>'.join(collected_lines)
                result_lines.append(merged_line)
            else:
                result_lines.append(current_line)
            
            i = j
        else:
            result_lines.append(current_line)
            i += 1
    
    return '\n'.join(result_lines)

def remove_javascript_void_zero(markdown_text: str) -> str:
    """ Remove '(javascript:void(0);)' or '(javascript:void(0))' from the content.
    idやclass属性が指定されていないaタグなどに取得すべき文字列が含まれることがあるため、
    excluded_selectorに指定できない。このためこの関数を用意し除する。
    aタグなどに含まれるケースについては、images/javascript_void_zero.png を参照。

    Args:
        content: The markdown content as a string.
    Returns:
        The modified markdown content without '(javascript:void(0);)' or '(javascript:void(0))' ."""
    return re.sub(r'\(javascript:void\\\(0\\\);?\)', '', markdown_text)

def adjust_numbered_lists(markdown_text: str) -> str:
    """
    Convert numbered lists to proper markdown format with dots.
    Handles:
    - Lines starting with numbers (1玉ねぎ → 1. 玉ねぎ)
    - Preserves existing proper format (1. already formatted)
    - Ignores numbers in middle of lines
    """
    lines = markdown_text.split('\n')
    adjusted_lines = []
    
    for line in lines:
        stripped = line.lstrip()
        leading_space = line[:len(line) - len(stripped)]
        
        # Pattern: starts with digit(s), no dot/space after, followed by content
        match = re.match(r'^(\d+)([^\.\s])', stripped, re.ASCII)
        
        if match:
            number = match.group(1)
            rest = stripped[len(number):]
            adjusted_line = f"{leading_space}{number}. {rest}"
            adjusted_lines.append(adjusted_line)
        else:
            adjusted_lines.append(line)
    return '\n'.join(adjusted_lines)

async def crawl(input_file='urls.txt', output_dir='output_crawled'):
    """Crawl the URLs from the input file and save the results to the output directory."""
    urls = []

    with open(input_file, 'r') as input_file:
        for line in input_file:
            url = line.strip()
            if url and len(url) > 0 and not url.startswith('#'):
                urls.append(url)



    if not Path(output_dir).exists():
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    # AsyncWebCrawlerは、Single browser instanceとして動作するため、複数のインスタスを生成すると
    # リソース逼迫によりハングアップするため、urlsのループ内で生成しないこと。
    async with AsyncWebCrawler() as crawler:
        for i, url in enumerate(urls):
            try:
                result = await crawler.arun(
                    url=url,
                    bypass_cache=True,
                    config=config,
                    
                )
                
                result_json = json.loads(result.model_dump_json(),)
                meta_data = {}
                meta_data["url"] = json.dumps(result_json["url"]).strip('"')
                print(f"url: {meta_data['url']}")

                for key, value in result_json["metadata"].items():
                    meta_data[key] = value
                
                # 指定出力ディレクトリの下にoutputディレクトリを作成してそこにメタデータとマークダウンを保存
                # メタデータとマークダウンは、データベースへのロード処理で一緒に使用する。           
                Path(f"{output_dir}/md").mkdir(parents=True, exist_ok=True)
                # mdディレクトリへメタデータを保存
                with open("{}/md/{}".format(output_dir, url2fname(url) + ".meta"), "w", encoding="utf-8") as file:
                    file.write(json.dumps(meta_data, ensure_ascii=False))
                # mdディレクトリへマークダウンを保存
                with open("{}/md/{}".format(output_dir, url2fname(url) + ".md"), "w") as file:
                    file.write(
                        # fix_multiline_table_cells(
                            adjust_numbered_lists(remove_javascript_void_zero(result.markdown))
                        # )
                    )
                # Unspan tables
                unspanner = TableUnspanner(result.html)
                result_list = []
                # Get all tables as markdown
                all_tables = unspanner.get_all_tables()
                for i, table in enumerate(all_tables):
                    markdown = unspanner.to_markdown_compact(table_index=i, header_row=0)
                    result_list.append(f"Table {i+1}:\n{markdown}\n\n\n\n")            

                # mdディレクトリへマークダウンを保存
                if len(result_list) > 0:
                    with open("{}/md/{}".format(output_dir, url2fname(url) + "_unspanned_tables.md"), "w", encoding="utf-8") as file:
                        file.write(''.join(result_list))

                # 出力ディレクトリ直下へcleaned HTML and JSONを保存
                if os.getenv("EXCUDE_CLEANED_HTML", "false").lower() == "true":
                    print("Skipping saving cleaned HTML as per EXCUDE_CLEANED_HTML setting.")
                else:
                    with open("{}/{}".format(output_dir, url2fname(url) + ".html"), "w") as file:
                        # file.write(result.cleaned_html)
                        file.write(result.html)

                if os.getenv("EXCUDE_JSON", "false").lower() == "true":
                    print("Skipping saving JSON as per EXCUDE_JSON setting.")
                else:
                    with open("{}/{}".format(output_dir, url2fname(url) + ".json"), "w", encoding="utf-8") as file:
                        file.write(json.dumps(result_json, indent=2, ensure_ascii=False))

                if i > 0 and i % 10 == 0:
                    await asyncio.sleep(0.5)               

            except Exception as e:
                print(f"Error processing {url}: {e}")
                exit(1)          

def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert url contents to markdown files"
    )
    parser.add_argument(
        'input_file',
        help='Path to the input url list file'
    )
    parser.add_argument(
        'output_dir',
        # '-o', '--output',
        help='Path to the output directory'
    )
    args = parser.parse_args()

    input_file = args.input_file
    output_dir = args.output_dir

    asyncio.run(crawl(input_file=input_file, output_dir=output_dir))
    exit(0)

if __name__ == "__main__":
    main()
    
    
