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



def fix_multiline_table_cells(content):
    """ Fix multiline table cells by merging lines that are part of the same cell.
    Args:
        content: The markdown content as a string.
    Returns:
        The modified markdown content with multiline cells merged."""
    lines = content.split('\n')
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

def remove_javascript_void_zero(content: str) -> str:
    """ Remove '(javascript:void(0);)' or '(javascript:void(0))' from the content.
    idやclass属性が指定されていないaタグなどに取得すべき文字列が含まれることがあるため、
    excluded_selectorに指定できない。このためこの関数を用意し除する。
    aタグなどに含まれるケースについては、images/javascript_void_zero.png を参照。

    Args:
        content: The markdown content as a string.
    Returns:
        The modified markdown content without '(javascript:void(0);)' or '(javascript:void(0))' ."""
    return re.sub(r'\(javascript:void\\\(0\\\);?\)', '', content)

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

    for url in urls:
        async with AsyncWebCrawler() as crawler:
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
                        remove_javascript_void_zero(result.markdown)
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
            
            # Wait for N seconds before processing the next URL
            # This can help prevent overwhelming the target server with too many requests in a short time period.
            # wait_seconds = 1
            # print(f"Waiting {wait_seconds} second(s) before processing next URL...")
            # await asyncio.sleep(wait_seconds)
        wait_seconds = 1
        print(f"Waiting {wait_seconds} second(s) before processing next URL...")
        time.sleep(1)  # Short delay between URLs to be polite to the server    

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

if __name__ == "__main__":
    main()
    
    
