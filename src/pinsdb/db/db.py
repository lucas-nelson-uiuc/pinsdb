import duckdb


def main():
    db = duckdb.connect()
    db.sql("SELECT * FROM read_csv_auto('/Users/lucasnelson/Desktop/open_source/pinsdb/.data/*/*.txt');")

if __name__ == "__main__":
    main()