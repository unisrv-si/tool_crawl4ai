"""
HTML Table Unspanner - Converts tables with rowspan/colspan to markdown
Compatible with Crawl4AI output
"""

import asyncio
from bs4 import BeautifulSoup
import pandas as pd


class TableUnspanner:
    """
    Unspans HTML tables with rowspan and colspan attributes
    and converts them to various formats including markdown
    """
    
    def __init__(self, html_content):
        """
        Initialize with HTML content
        
        Args:
            html_content: String containing HTML with table(s)
        """
        self.html_content = html_content
        self.soup = BeautifulSoup(html_content, 'html.parser')
    
    def unspan_table(self, table):
        """
        Unspan a single HTML table element
        
        Args:
            table: BeautifulSoup table element
            
        Returns:
            2D list representing the unspanned table grid
        """
        rows = table.find_all('tr')
        
        # Determine number of columns from colgroup if exists, else calculate
        colgroup = table.find('colgroup')
        if colgroup:
            max_cols = len(colgroup.find_all('col'))
        else:
            # Calculate from first row
            max_cols = sum(int(cell.get('colspan', 1)) 
                          for cell in rows[0].find_all(['td', 'th']))
        
        total_rows = len(rows)
        
        # Initialize grid
        grid = [['' for _ in range(max_cols)] for _ in range(total_rows)]
        
        # Fill the grid
        for row_idx, row in enumerate(rows):
            col_idx = 0
            
            for cell in row.find_all(['td', 'th']):
                # Find next available column
                while col_idx < max_cols and grid[row_idx][col_idx] != '':
                    col_idx += 1
                
                if col_idx >= max_cols:
                    break
                
                # Get cell attributes
                rowspan = int(cell.get('rowspan', 1))
                colspan = int(cell.get('colspan', 1))
                
                # Clean cell text
                text = cell.get_text(separator=' ', strip=True)
                text = ' '.join(text.split())
                
                # Fill grid with cell content
                for r in range(rowspan):
                    for c in range(colspan):
                        if row_idx + r < total_rows and col_idx + c < max_cols:
                            grid[row_idx + r][col_idx + c] = text
        
        return grid
    
    def get_all_tables(self):
        """
        Get all tables from the HTML content
        
        Returns:
            List of 2D lists, one for each table
        """
        tables = self.soup.find_all('table')
        return [self.unspan_table(table) for table in tables]
    
    def to_dataframe(self, table_index=0, header_row=0):
        """
        Convert a table to pandas DataFrame
        
        Args:
            table_index: Index of the table to convert (0-based)
            header_row: Row index to use as column headers
            
        Returns:
            pandas DataFrame
        """
        tables = self.get_all_tables()
        if table_index >= len(tables):
            raise IndexError(f"Table index {table_index} out of range. Found {len(tables)} tables.")
        
        grid = tables[table_index]
        
        if header_row is not None and len(grid) > header_row:
            headers = grid[header_row]
            data = grid[header_row + 1:]
            df = pd.DataFrame(data, columns=headers)
        else:
            df = pd.DataFrame(grid)
        
        return df
    
    def to_markdown(self, table_index=0, header_row=0, custom_headers=None):
        """
        Convert a table to markdown format
        
        Args:
            table_index: Index of the table to convert (0-based)
            header_row: Row index to use as column headers
            custom_headers: Optional list of custom header names to override
            
        Returns:
            Markdown formatted string
        """
        df = self.to_dataframe(table_index, header_row)
        
        # If custom headers provided, use them
        if custom_headers:
            df.columns = custom_headers
        
        return df.to_markdown(index=False)
    
    def to_markdown_compact(self, table_index=0, header_row=0, custom_headers=None):
        """
        Convert a table to compact markdown format without spaces in cells
        
        Args:
            table_index: Index of the table to convert (0-based)
            header_row: Row index to use as column headers
            custom_headers: Optional list of custom header names to override
            
        Returns:
            Compact markdown formatted string
        """
        tables = self.get_all_tables()
        if table_index >= len(tables):
            raise IndexError(f"Table index {table_index} out of range. Found {len(tables)} tables.")
        
        grid = tables[table_index]
        
        # Get headers and data
        if header_row is not None and len(grid) > header_row:
            headers = grid[header_row]
            data = grid[header_row + 1:]
        else:
            headers = [f"Col{i}" for i in range(len(grid[0]))]
            data = grid
        
        # Override with custom headers if provided
        if custom_headers:
            headers = custom_headers
        
        # Remove spaces from all cells
        headers_compact = [h.replace(' ', '') for h in headers]
        data_compact = [[cell.replace(' ', '') for cell in row] for row in data]
        
        # Build markdown manually
        lines = []
        
        # Header row
        lines.append('|' + '|'.join(headers_compact) + '|')
        
        # Separator row
        lines.append('|' + '|'.join([':---' for _ in headers]) + '|')
        
        # Data rows
        for row in data_compact:
            lines.append('|' + '|'.join(row) + '|')
        
        return '\n'.join(lines)
    
    def to_csv(self, table_index=0, header_row=0):
        """
        Convert a table to CSV format
        
        Args:
            table_index: Index of the table to convert (0-based)
            header_row: Row index to use as column headers
            
        Returns:
            CSV formatted string
        """
        df = self.to_dataframe(table_index, header_row)
        return df.to_csv(index=False)


# Example usage with Crawl4AI
async def crawl4ai_example():
    """
    Example of how to use TableUnspanner with Crawl4AI
    """
    import asyncio
    from crawl4ai import AsyncWebCrawler
    from simple_web_crawl import config

    url = 'https://www.tepco.co.jp/ep/private/plan2/chargelist03.html' 
    
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url=url,
            bypass_cache=True,
            config=config,
                    
                )    
    
    # Unspan tables
    unspanner = TableUnspanner(result.html)
    
    result_list = []
    # Get all tables as markdown
    all_tables = unspanner.get_all_tables()
    for i, table in enumerate(all_tables):
        # print(table)
        markdown = unspanner.to_markdown_compact(table_index=i, header_row=0)
        result_list.append(f"Table {i+1}:\n{markdown}\n\n\n\n")
    
    return result_list


if __name__ == "__main__":
    result_list = []
    result_list = asyncio.run(
        crawl4ai_example()
    )
    # Save to file
    with open('table_unspanner_example.md', 'w', encoding='utf-8') as f:
        for result in result_list:
            f.write(result)


    if False:
        # Test with the provided HTML
        html_content = """
        <table class="tbl-data-01" cellspacing="0" border="1">
        <colgroup>
        <col width="3%">
        <col width="9%">
        <col width="17%">
        <col width="7%">
        <col width="20%">
        </colgroup>
        <thead>
        <tr>
        <th colspan="3">&nbsp;</th>
        <th>単位</th>
        <th>料金（税込）</th>
        </tr>
        </thead>
        <tbody>
        <tr>
        <td rowspan="3" style="letter-spacing: 0.6rem; text-align: center;">基本料金</td>
        <td colspan="2">6kVA以下の場合</td>
        <td class="center">1契約</td>
        <td class="center">1,474円50銭</td>
        </tr>
        <tr>
        <td colspan="2">7kVA～10kVAの場合</td>
        <td class="center">〃</td>
        <td class="center">2,457円50銭</td>
        </tr>
        <tr>
        <td colspan="2">11kVA以上の場合</td>
        <td class="center">〃</td>
        <td class="center">2,457円50銭 ＋ 311円75銭 ×(契約容量 －10kVA)</td>
        </tr>
        <tr>
        <td rowspan="4" style="letter-spacing: 0.6rem; text-align: center;">電力量料金</td>
        <td rowspan="3">昼間時間</td>
        <td>最初の90kWhまで<br>(第1段階料金) </td>
        <td class="center">1kWh</td>
        <td class="center">31円80銭</td>
        </tr>
        <tr>
        <td>90kWhをこえ230kWhまで<br>(第2段階料金) </td>
        <td class="center">〃</td>
        <td class="center">39円10銭</td>
        </tr>
        <tr>
        <td>上記超過<br>(第3段階料金) </td>
        <td class="center">〃</td>
        <td class="center">43円62銭</td>
        </tr>
        <tr>
        <td colspan="2">夜間時間</td>
        <td class="center">〃</td>
        <td class="center">28円85銭</td>
        </tr>
        <tr>
        <td colspan="3">最低月額料金</td>
        <td class="center">1契約</td>
        <td class="center">330円44銭</td>
        </tr>
        </tbody>
        </table>
        """
        
        unspanner = TableUnspanner(html_content)
        
        # Print unspanned grid
        print("Unspanned Table Grid:")
        print("=" * 100)
        grid = unspanner.get_all_tables()[0]
        for row in grid:
            print(row)
        
        # Print markdown with custom headers
        print("\n\nMarkdown Format with Custom Headers:")
        print("=" * 100)
        custom_headers = ['', '', '', '単位', '料金（税込）']
        markdown = unspanner.to_markdown(header_row=0, custom_headers=custom_headers)
        print(markdown)
        
        # Print compact markdown (no spaces)
        print("\n\nCompact Markdown Format (No Spaces):")
        print("=" * 100)
        markdown_compact = unspanner.to_markdown_compact(header_row=0, custom_headers=custom_headers)
        print(markdown_compact)
        
        # Save to file
        with open('table_unspanner_example.md', 'w', encoding='utf-8') as f:
            f.write("# Electric Rate Table\n\n")
            f.write("## Regular Markdown Format\n\n")
            f.write(markdown)
            f.write("\n\n## Compact Markdown Format (No Spaces)\n\n")
            f.write(markdown_compact)
        
        print("\n\nSaved to: table_unspanner_example.md")
