\# DealHunter Portfolio



A Python-based product analysis and profit estimation application.



This project demonstrates Python programming, product identification,

SQLite database management, and automated software testing.



\## Overview



DealHunter Portfolio analyzes sample product listings, categorizes

products, estimates potential resale profits, and stores results

in a SQLite database.



This is a standalone educational demonstration inspired by a larger

private software project.



\## Features



\- Product identification using Python regular expressions

\- Profit calculations including purchase price, shipping, and fees

\- SQLite database storage

\- Duplicate product detection

\- Automated unit testing

\- Modular Python application structure



\## Technologies



\- Python 3

\- SQLite

\- SQL

\- Regular Expressions

\- Python unittest



\## Project Structure



\- profit\_calculator.py â€” Calculates estimated profits

\- product\_matcher.py â€” Identifies product categories

\- database.py â€” Saves and retrieves product information

\- test\_profit\_calculator.py â€” Tests profit calculations

\- test\_database.py â€” Tests database operations



\## Getting Started



Requirements: Python 3



Run the profit calculator:



```bash

python profit\_calculator.py

```



Run the product matcher:



```bash

python product\_matcher.py

```



Run the database demonstration:



```bash

python database.py

```



Run automated tests:



```bash

python -m unittest discover -v

```



\## Example Output



```text

Product: John Deere Z930M Mower Part

Model: Z930M

Category: LAWN MOWER PART

Expected Profit: $180.00

```



All examples use fictional purchase and resale prices.



\## Current Limitations



\- Product identification uses basic matching rules.

\- Duplicate detection is based on product titles.

\- Resale values are supplied as sample inputs, not live market estimates.

\- The application does not automatically purchase products.



\## Future Improvements



\- More advanced product matching

\- Improved database validation

\- CSV import and export

\- Command-line interface

\- Additional automated tests



\## Project Purpose



Built to demonstrate practical Python development,

database management, problem-solving, and automated testing.



The original DealHunter application is maintained separately

as a private project.
