import streamlit as st

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def remote_css(url):
    st.markdown(f'''
                <head>
                    <!-- Material Icons -->
                    <link href="{url}" rel="stylesheet">
                </head>
                ''', unsafe_allow_html=True)   