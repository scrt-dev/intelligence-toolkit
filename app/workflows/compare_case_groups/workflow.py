# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project.
#
import os

import polars as pl
import streamlit as st

import app.util.example_outputs_ui as example_outputs_ui
import app.workflows.compare_case_groups.variables as gn_variables
from app.util import ui_components
from toolkit.compare_case_groups import prompts
from toolkit.compare_case_groups.build_dataframes import (
    build_attribute_df,
    build_grouped_df,
    build_ranked_df,
    filter_df,
)
from toolkit.compare_case_groups.temporal_process import (
    build_temporal_data,
    create_window_df,
)
from toolkit.helpers.df_functions import fix_null_ints


def get_intro() -> str:
    file_path = os.path.join(os.path.dirname(__file__), "README.md")
    with open(file_path) as file:
        return file.read()


def create(sv: gn_variables.SessionVariables, workflow=None):
    ui_components.check_ai_configuration()

    intro_tab, prepare_tab, summarize_tab, generate_tab, examples_tab = st.tabs(
        [
            "Compare case groups workflow:",
            "Prepare case data",
            "Specify group comparisons",
            "Generate AI group reports",
            "View example outputs"
        ]
    )

    with intro_tab:
        st.markdown(get_intro())
    with prepare_tab:
        uploader_col, model_col = st.columns([1, 1])
        with uploader_col:
            ui_components.single_csv_uploader(
                workflow,
                "Upload CSV to compare",
                sv.case_groups_last_file_name,
                sv.case_groups_input_df,
                sv.case_groups_final_df,
                key="group_comparison_uploader",
                height=400,
            )
        with model_col:
            ui_components.prepare_input_df(
                workflow,
                sv.case_groups_input_df,
                sv.case_groups_final_df,
            )
            sv.case_groups_final_df.value = fix_null_ints(sv.case_groups_final_df.value)
    with summarize_tab:
        if len(sv.case_groups_final_df.value) == 0:
            st.warning("Upload data to continue.")
        else:
            c1, c2 = st.columns([1, 2])
            with c1:
                st.markdown("##### Define summary model")
                sorted_atts = []
                sorted_cols = sorted(sv.case_groups_final_df.value.columns)

                for col in sorted_cols:
                    vals = [
                        f"{col}:{x}"
                        for x in sorted(
                            sv.case_groups_final_df.value[col].astype(str).unique()
                        )
                        if x
                        not in [
                            "",
                            "<NA>",
                            "nan",
                            "NaN",
                            "None",
                            "none",
                            "NULL",
                            "null",
                        ]
                    ]
                    sorted_atts.extend(vals)

                groups = st.multiselect(
                    "Compare groups of records with different combinations of these attributes:",
                    sorted_cols,
                    default=sv.case_groups_groups.value,
                )
                aggregates = st.multiselect(
                    "Using counts of these attributes:",
                    sorted_cols,
                    default=sv.case_groups_aggregates.value,
                )
                temporal_options = ["", *sorted_cols]
                temporal = st.selectbox(
                    "Across windows of this temporal/ordinal attribute (optional):",
                    temporal_options,
                    index=temporal_options.index(sv.case_groups_temporal.value),
                )
                filters = st.multiselect(
                    "After filtering to records matching these values (optional):",
                    sorted_atts,
                    default=sv.case_groups_filters.value,
                )

                create = st.button(
                    "Create data summary", disabled=len(groups) == 0 or len(aggregates) == 0
                )

            with c2:
                st.markdown("##### Data summary")
                if create:
                    sv.case_groups_filters.value = filters
                    sv.case_groups_groups.value = groups
                    sv.case_groups_aggregates.value = aggregates
                    sv.case_groups_temporal.value = temporal

                    for group in sv.case_groups_groups.value:
                        sv.case_groups_final_df.value = sv.case_groups_final_df.value[
                            sv.case_groups_final_df.value[group] != ""
                        ]

                    sv.case_groups_model_df.value = sv.case_groups_final_df.value.copy(
                        deep=True
                    )

                    sv.case_groups_model_df.value = (
                        sv.case_groups_model_df.value.replace("", None)
                    )
                    initial_row_count = len(sv.case_groups_model_df.value)

                    filtered_df = (
                        filter_df(sv.case_groups_model_df.value, filters)
                        if len(filters) > 0
                        else sv.case_groups_model_df.value
                    )

                    grouped_df = build_grouped_df(filtered_df, groups)

                    attributes_df = build_attribute_df(
                        pl.from_pandas(filtered_df), groups, aggregates
                    )

                    temporal_df = pl.DataFrame()
                    temporal_atts = []
                    # create Window df
                    if temporal is not None and temporal != "":
                        window_df = create_window_df(
                            groups, temporal, aggregates, pl.from_pandas(filtered_df)
                        )

                        temporal_atts = sorted(
                            sv.case_groups_model_df.value[temporal].astype(str).unique()
                        )

                        temporal_df = build_temporal_data(
                            window_df, groups, temporal_atts, temporal
                        )
                    # Create overall df
                    ranked_df = build_ranked_df(
                        temporal_df,
                        pl.from_pandas(grouped_df),
                        attributes_df,
                        temporal or "",
                        groups,
                    )
                    ranked_df = ranked_df.to_pandas()

                    sv.case_groups_model_df.value = (
                        ranked_df[
                            [
                                *[g.lower() for g in groups],
                                "group_count",
                                "group_rank",
                                "attribute_value",
                                "attribute_count",
                                "attribute_rank",
                                f"{temporal}_window",
                                f"{temporal}_window_count",
                                f"{temporal}_window_rank",
                                f"{temporal}_window_delta",
                            ]
                        ]
                        if temporal != ""
                        else ranked_df[
                            [
                                *[g.lower() for g in groups],
                                "group_count",
                                "group_rank",
                                "attribute_value",
                                "attribute_count",
                                "attribute_rank",
                            ]
                        ]
                    )
                    groups_text = (
                        "[" + ", ".join(["**" + g + "**" for g in groups]) + "]"
                    )
                    filters_text = (
                        "["
                        + ", ".join(
                            ["**" + f.replace(":", "\\:") + "**" for f in filters]
                        )
                        + "]"
                    )

                    filtered_row_count = len(filtered_df)
                    dataset_proportion = int(
                        round(
                            100 * filtered_row_count / initial_row_count
                            if initial_row_count > 0
                            else 0,
                            0,
                        )
                    )
                    description = "This table shows:"
                    description += (
                        f"\n- A summary of **{len(filtered_df)}** data records matching {filters_text}, representing **{dataset_proportion}%** of the overall dataset with values for all grouping attributes"
                        if len(filters) > 0
                        else f"\n- A summary of all **{initial_row_count}** data records with values for all grouping attributes"
                    )
                    description += f"\n- The **group_count** of records for all {groups_text} groups, and corresponding **group_rank**"
                    description += f"\n- The **attribute_count** of each **attribute_value** for all {groups_text} groups, and corresponding **attribute_rank**"
                    if temporal != "":
                        description += f"\n- The **{temporal}_window_count** of each **attribute_value** for each **{temporal}_window** for all {groups_text} groups, and corresponding **{temporal}_window_rank**"
                        description += f"\n- The **{temporal}_window_delta**, or change in the **attribute_value_count** for successive **{temporal}_window** values, within each {groups_text} group"
                    sv.case_groups_description.value = description
                    st.rerun()
                if len(sv.case_groups_model_df.value) > 0:
                    st.dataframe(
                        sv.case_groups_model_df.value,
                        hide_index=True,
                        use_container_width=True,
                        height=500,
                    )

                    st.markdown(sv.case_groups_description.value)
                    st.download_button(
                        "Download data summary",
                        data=sv.case_groups_model_df.value.to_csv(
                            index=False, encoding="utf-8-sig"
                        ),
                        file_name="group_data_summary.csv",
                        mime="text/csv",
                    )

    with generate_tab:
        if len(sv.case_groups_model_df.value) == 0:
            st.warning("Prepare data summary to continue.")
        else:
            c1, c2 = st.columns([1, 1])
            with c1:
                st.markdown("##### Data summary filters")
                groups = sorted(
                    sv.case_groups_model_df.value.groupby(
                        sv.case_groups_groups.value
                    ).groups.keys()
                )
                b1, b2 = st.columns([1, 1])
                with b1:
                    selected_groups = st.multiselect(
                        "Select specific groups to report on:",
                        list(groups),
                        default=sv.case_groups_selected_groups.value,
                    )
                with b2:
                    top_group_ranks = st.number_input(
                        "OR Select top group ranks to report on:",
                        min_value=0,
                        max_value=9999999999,
                        value=sv.case_groups_top_groups.value,
                    )
                fdf = sv.case_groups_model_df.value.copy(deep=True)
                filter_description = ""
                if len(selected_groups) > 0:
                    fdf = fdf[
                        fdf.set_index(sv.case_groups_groups.value).index.isin(
                            selected_groups
                        )
                    ]
                    filter_description = f'Filtered to the following groups only: {", ".join([str(s) for s in selected_groups])}'
                elif top_group_ranks:
                    fdf = fdf[fdf["group_rank"] <= top_group_ranks]
                    filter_description = (
                        f"Filtered to the top {top_group_ranks} groups by record count"
                    )
                num_rows = len(fdf)
                st.markdown(f"##### Filtered data summary to report on ({num_rows} rows)")
                st.dataframe(fdf, hide_index=True, use_container_width=True, height=280)
                variables = {
                    "description": sv.case_groups_description.value,
                    "dataset": fdf.to_csv(index=False, encoding="utf-8-sig"),
                    "filters": filter_description,
                }
                generate, messages, reset = ui_components.generative_ai_component(
                    sv.case_groups_system_prompt, variables
                )
                if reset:
                    sv.case_groups_system_prompt.value["user_prompt"] = (
                        prompts.user_prompt
                    )
                    st.rerun()
            with c2:
                st.markdown("##### Group comparison report")

                narrative_placeholder = st.empty()
                gen_placeholder = st.empty()
                if generate:
                    sv.case_groups_selected_groups.value = selected_groups
                    sv.case_groups_top_groups.value = top_group_ranks

                    on_callback = ui_components.create_markdown_callback(
                        narrative_placeholder
                    )
                    result = ui_components.generate_text(
                        messages, callbacks=[on_callback]
                    )
                    sv.case_groups_report.value = result

                    # validation, messages_to_llm = ui_components.validate_ai_report(
                    #     messages, result
                    # )
                    # sv.case_groups_report_validation.value = validation
                    # sv.case_groups_report_validation_messages.value = messages_to_llm
                    st.rerun()
                else:
                    if sv.case_groups_report.value == "":
                        gen_placeholder.warning(
                            "Press the Generate button to create an AI report for the selected groups."
                        )
                narrative_placeholder.markdown(sv.case_groups_report.value)

                ui_components.report_download_ui(sv.case_groups_report, "group_report")

                # ui_components.build_validation_ui(
                #     sv.case_groups_report_validation.value,
                #     sv.case_groups_report_validation_messages.value,
                #     sv.case_groups_report.value,
                #     workflow,
                # )
    with examples_tab:
        example_outputs_ui.create_example_outputs_ui(examples_tab, workflow)

