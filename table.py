from st_aggrid import GridOptionsBuilder, AgGrid, JsCode

gridOptions = {
    "defaultColDef": {
        "minWidth": 5,
        "filter": True,
        "resizable": True,
        "sortable": True,
        "tooltipShowDelay": 0,  # Set tooltip delay to zero
    },
    "columnDefs": [
        {
            "headerName": "start_date",
            "field": "start_date",
            "type": ["dateColumnFilter", "customDateTimeFormat"],
            "custom_format_string": "yyyy-MM-dd",
            "pivot": True,
            "checkboxSelection": True,
        },
        {
            "headerName": "end_date",
            "field": "end_date",
            "type": ["dateColumnFilter", "customDateTimeFormat"],
            "custom_format_string": "yyyy-MM-dd",
            "pivot": True,
        },
        {
            "headerName": "POL",
            "field": "POL",
            "type": ["string"],
        },
        {
            "headerName": "POD",
            "field": "POD",
            "type": ["string"],
        },
        {
            "headerName": "customer",
            "field": "customer",
            "type": ["string"],
        },
        {
            "headerName": "email",
            "field": "email",
            "type": ["string"],
            "cellRenderer": JsCode(""" function(params) { return params.value }; """),
        },
    ],
    "rowSelection": "multiple",
    "rowMultiSelectWithClick": False,
    "suppressRowDeselection": False,
    "suppressRowClickSelection": True,
    "groupSelectsChildren": True,
    "groupSelectsFiltered": True,
    "domLayout": "normal",
}


def create_aggrid(df_requests):
    table_data = AgGrid(
        df_requests.copy(),
        gridOptions=gridOptions,
        height=300,
        width="100%",
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
    )
    return table_data
