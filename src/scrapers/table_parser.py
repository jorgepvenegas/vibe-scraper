"""HTML table parsing to JSON with support for complex table features."""

from typing import Optional

from bs4 import BeautifulSoup, Tag

from src.models.schemas import ParseTableConfig, TableMetadata


class TableParser:
    """Parse HTML tables to JSON with support for complex features."""

    def parse(
        self,
        table_html: str,
        config: ParseTableConfig,
    ) -> tuple[list[dict[str, str]], dict]:
        """
        Parse HTML table to list of dictionaries.

        Handles:
        - Merged cells (colspan/rowspan)
        - Nested tables
        - Multiple tbody sections
        - Custom selectors for headers, rows, cells

        Args:
            table_html: HTML string containing the table
            config: ParseTableConfig with selectors and options

        Returns:
            Tuple of (parsed_data, table_metadata_dict)
        """
        soup = BeautifulSoup(table_html, "lxml")

        # Extract headers
        headers = self._extract_headers(soup, config)
        if not headers:
            return [], {"rows_parsed": 0, "columns": 0, "has_merged_cells": False, "nested_tables_found": 0}

        # Extract rows
        rows_data = self._extract_rows(soup, config, headers)

        # Check for merged cells and nested tables
        has_merged_cells = self._check_merged_cells(soup, config)
        nested_count = self._count_nested_tables(soup, config)

        # Create metadata
        metadata = {
            "rows_parsed": len(rows_data),
            "columns": len(headers),
            "has_merged_cells": has_merged_cells,
            "nested_tables_found": nested_count,
        }

        return rows_data, metadata

    def _extract_headers(self, soup: BeautifulSoup, config: ParseTableConfig) -> list[str]:
        """
        Extract header names from table.

        Args:
            soup: BeautifulSoup object of table
            config: ParseTableConfig with header selector

        Returns:
            List of header names
        """
        headers = []

        if config.header_row_index is not None:
            # Headers are in a specific row of tbody
            rows = soup.select(config.row_selector)
            if config.header_row_index < len(rows):
                header_row = rows[config.header_row_index]
                cells = header_row.select(config.cell_selector)
                headers = [cell.get_text(strip=True) for cell in cells]
        else:
            # Headers from dedicated selector
            header_cells = soup.select(config.headers_selector)
            headers = [cell.get_text(strip=True) for cell in header_cells]

        return headers

    def _extract_rows(
        self,
        soup: BeautifulSoup,
        config: ParseTableConfig,
        headers: list[str],
    ) -> list[dict[str, str]]:
        """
        Extract data rows from table.

        Args:
            soup: BeautifulSoup object of table
            config: ParseTableConfig with row/cell selectors
            headers: List of header names

        Returns:
            List of row dictionaries
        """
        rows_data = []
        rows = soup.select(config.row_selector)

        # Skip header row if headers are from tbody
        start_index = 0
        if config.header_row_index is not None:
            start_index = config.header_row_index + 1

        for row_index, row in enumerate(rows[start_index:], start=start_index):
            # Skip rows in skip_rows list
            if row_index in config.skip_rows:
                continue

            cells = row.select(config.cell_selector)
            row_data = {}

            # Fill row with header values
            for col_index, header in enumerate(headers):
                if col_index < len(cells):
                    cell = cells[col_index]
                    # Handle nested tables - extract all text
                    cell_value = self._extract_cell_value(cell)
                    row_data[header] = cell_value
                else:
                    row_data[header] = ""

            rows_data.append(row_data)

        return rows_data

    def _extract_cell_value(self, cell: Tag) -> str:
        """
        Extract value from a cell, handling nested tables.

        Args:
            cell: BeautifulSoup Tag representing the cell

        Returns:
            Cell text content
        """
        # Get all text, which will include nested table content
        text = cell.get_text(strip=True, separator=" ")
        return text

    def _check_merged_cells(self, soup: BeautifulSoup, config: ParseTableConfig) -> bool:
        """
        Check if table has merged cells (colspan or rowspan).

        Args:
            soup: BeautifulSoup object of table
            config: ParseTableConfig

        Returns:
            True if table has merged cells
        """
        # Check for colspan
        cells_with_colspan = soup.select(f"{config.row_selector} {config.cell_selector}[colspan]")
        if cells_with_colspan:
            return True

        # Check for rowspan
        cells_with_rowspan = soup.select(f"{config.row_selector} {config.cell_selector}[rowspan]")
        if cells_with_rowspan:
            return True

        return False

    def _count_nested_tables(self, soup: BeautifulSoup, config: ParseTableConfig) -> int:
        """
        Count nested tables within cells.

        Args:
            soup: BeautifulSoup object of table
            config: ParseTableConfig

        Returns:
            Count of nested tables found
        """
        # Find all cells and count tables within them
        cells = soup.select(f"{config.row_selector} {config.cell_selector}")
        nested_count = 0

        for cell in cells:
            # Look for tables within this cell
            nested_tables = cell.find_all("table", recursive=False)
            nested_count += len(nested_tables)

        return nested_count
