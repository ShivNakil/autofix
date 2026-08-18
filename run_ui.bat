@echo off
REM Batch file to run the AutoFix Agent Streamlit UI

:: Activate virtual environment if it exists
if exist .venv\Scripts\activate (
    call .venv\Scripts\activate
) else if exist venv\Scripts\activate (
    call venv\Scripts\activate
)

:: Install streamlit if not already installed
pip install streamlit

:: Run the Streamlit app
streamlit run streamlit_app.py