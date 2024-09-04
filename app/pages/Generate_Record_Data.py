# noqa: N999
# Copyright (c) 2024 Microsoft Corporation. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project.
#
import streamlit as st
import app.workflows.generate_record_data.variables as bds_variables
import app.workflows.generate_record_data.workflow
from components.app_loader import load_multipage_app
from util.helper_fn import app_in_dev_mode

workflow = "generate_record_data"


def main():
    st.set_page_config(
        layout="wide",
        initial_sidebar_state="collapsed",
        page_icon="app/myapp.ico",
        page_title="Intelligence Toolkit | Generate Record Data",
    )
    sv = bds_variables.SessionVariables(workflow)
    load_multipage_app(sv)

    try:
        app.workflows.generate_record_data.workflow.create(sv, workflow)
    except Exception as e:
        if app_in_dev_mode():
            st.exception(e)
        else:
            st.error(f"An error occurred: {e}")


if __name__ == "__main__":
    main()