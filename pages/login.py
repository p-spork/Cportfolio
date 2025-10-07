import streamlit as st
# gonna have to import from other .py files

st.set_page_config(
    page_title="Hello"
)
st.write("Welcome to Cportfolio!")

st.sidebar.success("Select a demo above.") #useful for next pages but maybe not login page? 

st.markdown(
    """
    this is where the user login username + password will be and then a login button
"""
)
