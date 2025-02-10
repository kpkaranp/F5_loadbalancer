jobs:
  run-qkview-backup:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.8'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run QKView Backup Script
        env:
          API_USERNAME: ${{ secrets.API_USERNAME }}
          API_PASSWORD: ${{ secrets.API_PASSWORD }}
        run: python backup_qkview.py
