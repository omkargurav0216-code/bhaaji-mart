# Grocery Management System

A Flask-based Grocery Management System with cart, payments, analytics, and admin dashboard.

---

## Download / Clone Instructions

### Method A: Clone with Git
Run the following command in your terminal:
```bash
git clone https://github.com/omkargurav0216-code/bhaaji-mart.git
```

### Method B: Download ZIP
1. Click **Code** -> **Download ZIP** on GitHub.
2. Extract the downloaded ZIP file to a folder.

---

## Windows Setup

1. Open your terminal or Command Prompt (CMD).
2. Navigate to the project directory:
   ```cmd
   cd bhaaji-mart-main
   ```
3. Create a virtual environment (recommended):
   ```cmd
   python -m venv venv
   ```
4. Activate the virtual environment:
   ```cmd
   venv\Scripts\activate
   ```
5. Install the required dependencies:
   ```cmd
   pip install -r requirements.txt
   ```
6. Create a `.env` file in the project root directory (see Environment Variables Setup section below).

7. Run the application:
   ```cmd
   python -m backend.app
   ```

---

## Linux / macOS Setup

1. Open your terminal.
2. Navigate to the project directory:
   ```bash
   cd Grocery_Python06-main
   ```
3. Create a virtual environment:
   ```bash
   python3 -m venv venv
   ```
4. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```
5. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
6. Create a `.env` file in the project root directory (see Environment Variables Setup section below).

7. Run the application:
   ```bash
   python3 -m backend.app
   ```

---
## Environment Variables Setup

Before running the application, create a `.env` file in the project root directory.

### Project Structure

```text
bhaaji-mart/
│
├── backend/
├── static/
├── templates/
├── .env
├── requirements.txt
└── README.md
```

### Create a `.env` File

Create a file named `.env` and add your Stripe Secret Key:

```env
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key_here
```

Replace:

```env
sk_test_your_stripe_secret_key_here
```

with your actual Stripe Test Secret Key from your Stripe Dashboard.

### Example

```env
STRIPE_SECRET_KEY=sk_test_51xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```
### Security Notice

Never commit your `.env` file to GitHub.

Add the following entry to your `.gitignore` file:

```gitignore
.env
```

This prevents accidental exposure of your Stripe Secret Key.

---

## Project Structure

```text
backend/
templates/
static/
requirements.txt
```

---

## Important Notes

* **Python Version**: Python 3.10+ is highly recommended.
* **Environment Variables**: A `.env` file containing `STRIPE_SECRET_KEY` is required before running the application.
* **Stripe Mode**: Stripe runs in Test Mode.
* **Network Connectivity**: An active internet connection is required for Stripe test payment processing.

---

## Troubleshooting

### `ModuleNotFoundError`
* **Cause**: Dependencies are not installed or the virtual environment is not active.
* **Fix**: Ensure your virtual environment is activated (`venv\Scripts\activate` or `source venv/bin/activate`) and run `pip install -r requirements.txt`.

### `pip: command not found`
* **Cause**: Python is not added to your system path.
* **Fix**: Reinstall Python and ensure the checkbox "Add Python to PATH" is checked during installation.

### Port 5000 Already in Use
* **Cause**: Another service or server is running on port 5000.
* **Fix**: Stop the existing service or run the Flask app on a different port:
  ```bash
  python -m backend.app --port 8000
  ```
---

## License

This project is intended for educational and learning purposes.