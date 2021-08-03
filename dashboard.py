import os
os.environ['TF_XLA_FLAGS'] = '--tf_xla_enable_xla_devices'
import sys
import getopt
import streamlit as st
import json
#import SessionState
# import tkinter as tk
# from tkinter import filedialog
import time

import pandas as pd

from model_prediction import model_predictor_nlb as pr
import lstm as training

#---Workaround for "tensorflow.python.framework.errors_impl.UnknownError: Fail to find the dnn implementation."
from tensorflow.compat.v1 import ConfigProto
from tensorflow.compat.v1 import InteractiveSession
config = ConfigProto()
config.gpu_options.allow_growth = True # dynamically grow the memory used on the GPU
#config.inter_op_parallelism_threads = 4
config.intra_op_parallelism_threads = 4
session = InteractiveSession(config=config)
#-----

st.set_page_config(layout="wide", initial_sidebar_state="auto", page_title='NxEventPred', page_icon="🎯")

#Page Customization
max_width_str = f"max-width: 1500px;"
st.markdown(
	f"""
		<style>
			.reportview-container .main .block-container {{{max_width_str}}}
		</style>    
	""",
	unsafe_allow_html=True
)

#Condense the layout
padding = 1
st.markdown(f""" <style>
    .reportview-container .main .block-container{{
        padding-top: {padding}rem;
        padding-right: {padding}rem;
        padding-left: {padding}rem;
        padding-bottom: {padding}rem;
    }} </style> """, unsafe_allow_html=True)

# #Hide the menu button
# st.markdown(""" <style>
# #MainMenu {visibility: hidden;}
# footer {visibility: hidden;}
# </style> """, unsafe_allow_html=True)


def catch_parameter(opt):
    """Change the captured parameters names"""
    switch = {'-h': 'help', '-o': 'one_timestamp', '-a': 'activity',
              '-f': 'file_name', '-i': 'imp', '-l': 'lstm_act',
              '-d': 'dense_act', '-p': 'optim', '-n': 'norm_method',
              '-m': 'model_type', '-z': 'n_size', '-y': 'l_size',
              '-c': 'folder', '-b': 'model_file', '-x': 'is_single_exec',
              '-t': 'max_trace_size', '-e': 'splits', '-g': 'sub_group',
              '-v': 'variant', '-r': 'rep'}
    try:
        return switch[opt]
    except:
        raise Exception('Invalid option ' + opt)


def main(argv, filter_parms=None, filter_parameter=None):

    navigate_page = st.sidebar.selectbox("🔗 Navigate", ["Home", "Training", "About"], key="navigation_page")
    if navigate_page == "Training":
        training.main(argv)
        #st.write("Dashboard coming Up")
    # elif navigate_page == "ℹ️About":

    elif navigate_page == "Home":
        #Dashboard Title
        st.title("⏭️Next Event Prediction Dashboard") #Adding title bar
        st.sidebar.title("🎛️ App Control Menu")  #Adding the header to the sidebar as well as the sidebar
        #st.sidebar.markdown("""---""")
        #st.markdown("This dashboard is used to *predict* and *recommend* next event for the provided eventlog")

        parameters = dict()
        column_names = {'Case ID': 'caseid',
                        'Activity': 'task',
                        'lifecycle:transition': 'event_type',
                        'Resource': 'user'}
        parameters['one_timestamp'] = True  # Only one timestamp in the log

        if not argv:
            # Type of LSTM task -> training, pred_log
            # pred_sfx, predict_next
            #parameters['activity'] = classifier
            parameters['activity'] = 'predict_next' # Change Here
            # Event-log reading parameters
            parameters['read_options'] = {
                'timeformat': '%Y-%m-%dT%H:%M:%S.%f',
                'column_names': column_names,
                'one_timestamp': parameters['one_timestamp'],
                'ns_include': True}

            # Folder picker button
            if parameters['activity'] in ['pred_log', 'pred_sfx', 'predict_next']:

                #--Hard Coded Value
                parameters['is_single_exec'] = True  # single or batch execution
                parameters['rep'] = 1
                with st.sidebar.beta_expander('Folder Name'):
                    st.info("Provide the folder for which the prediction has to be simulated")
                    _folder_name  = st.text_input('', key="folder_name")
                #st.sidebar.markdown("""---""")
                parameters['folder'] = _folder_name

                if parameters['folder'] != "":
                    #--Selecting Model
                    _model_directory = os.path.join('output_files', _folder_name)
                    _model_name = []
                    for file in os.listdir(_model_directory):
                        # check the files which are end with specific extention
                        if file.endswith(".h5"):
                            _model_name.append(file)
                    parameters['model_file'] = _model_name[-1]

                    #--Selecting Mode
                    with st.sidebar.beta_expander('Type of Prediction Processing Mode'):
                        st.info("Select **Batch Processing** for the prediction of eintire log file,"
                                " **Single Processing** to simulate the prediction for each Case Id individually")
                        #next_option = st.sidebar.radio('', ['Execution Mode', 'Evaluation Mode'])
                        #st.sidebar.subheader("Choose Mode of Prediction")
                        _mode_sel = st.radio('Processing', ['Batch Processing', 'Single Event Processing'], key="processing_type")
                    #st.sidebar.markdown("""---""")

                    if _mode_sel == 'Batch Processing':
                        _mode_sel = 'batch'
                    elif _mode_sel == 'Single Event Processing':
                        _mode_sel = 'next'

                    parameters['mode'] = _mode_sel

            else:
                raise ValueError(parameters['activity'])
        else:
            # Catch parameters by console
            try:
                opts, _ = getopt.getopt(
                    argv,
                    "ho:a:f:i:l:d:p:n:m:z:y:c:b:x:t:e:v:r:",
                    ['one_timestamp=', 'activity=',
                     'file_name=', 'imp=', 'lstm_act=',
                     'dense_act=', 'optim=', 'norm_method=',
                     'model_type=', 'n_size=', 'l_size=',
                     'folder=', 'model_file=', 'is_single_exec=',
                     'max_trace_size=', 'splits=', 'sub_group=',
                     'variant=', 'rep='])
                for opt, arg in opts:
                    key = catch_parameter(opt)
                    if arg in ['None', 'none']:
                        parameters[key] = None
                    elif key in ['is_single_exec', 'one_timestamp']:
                        parameters[key] = arg in ['True', 'true', 1]
                    elif key in ['imp', 'n_size', 'l_size',
                                 'max_trace_size','splits', 'rep']:
                        parameters[key] = int(arg)
                    else:
                        parameters[key] = arg
                parameters['read_options'] = {'timeformat': '%Y-%m-%dT%H:%M:%S.%f',
                                              'column_names': column_names,
                                              'one_timestamp':
                                                  parameters['one_timestamp'],
                                                  'ns_include': True}
            except getopt.GetoptError:
                print('Invalid option')
                sys.exit(2)

        def _list2dictConvert(_a):
            _it = iter(_a)
            _res_dct = dict(zip(_it, _it))
            return _res_dct

        # if parameters['mode'] in ['next']:
        #     #   Saves the result in the URL in the Next mode
        #     app_state = st.experimental_get_query_params()
        #     if "my_saved_result" in app_state:
        #         saved_result = app_state["my_saved_result"][0]
        #         nxt_button_idx = int(saved_result)
        #         #st.write("Here is your result", saved_result)
        #     else:
        #         st.write("No result to display, compute a value first.")
        #         nxt_button_idx = 0




        @st.cache(persist=True)
        def read_next_testlog():
            input_file = os.path.join('output_files', parameters['folder'], 'parameters', 'test_log.csv')
            parameter_file = os.path.join('output_files', parameters['folder'], 'parameters', 'model_parameters.json')
            filter_log = pd.read_csv(input_file, dtype={'user': str})
            # Standard Code based on log_reader
            filter_log = filter_log.rename(columns=column_names)
            filter_log = filter_log.astype({'caseid': object})
            filter_log = (filter_log[(filter_log.task != 'Start') & (filter_log.task != 'End')].reset_index(drop=True))
            filter_log_columns = filter_log.columns
            with open(parameter_file) as pfile:
                parameter_data = json.load(pfile)
                file_name = parameter_data["file_name"]
                pfile.close()
            return filter_log, filter_log_columns, file_name

        def next_columns(filter_log, display_columns):
            # Dashboard selection of Case ID
            filter_caseid = st.selectbox("🆔 Select Case ID", filter_log["caseid"].unique(), key="caseid_select")
            filter_caseid_attr_df = filter_log.loc[filter_log["caseid"].isin([filter_caseid])]
            filter_attr_display = filter_caseid_attr_df[display_columns]
            return filter_attr_display, filter_caseid, filter_caseid_attr_df

        def num_predictions(_df):

            if _df['task'].nunique() > _df['role'].nunique():
                _dfmax = _df['role'].nunique()
            elif _df['role'].nunique() > _df['task'].nunique():
                _dfmax = _df['task'].nunique()
            else:
                _dfmax = _df['task'].nunique()

            with st.sidebar.beta_expander('Variant'):
                st.info("Select the slider value **equal to 1** for **Max Probability** "
                        "otherwise choose the number **greater than 1** for "
                        "**Multiple Predictions** sorted in decreasing order based on probability of it's ocurrance")

                # if 'my_number_prediction_slider' not in st.session_state:
                #     st.session_state['my_number_prediction_slider'] = 0
                #
                # print("What is Happening :", st.session_state['my_number_prediction_slider'])

                slider = st.slider(
                    label='', min_value=1,
                    max_value=_dfmax, key='my_number_prediction_slider')

            return slider

        def label_identifier(file_name):
            # ---Logic to be added for other dataset
            with st.sidebar.beta_expander('Type of Single Event Processing'):
                if "sepsis" in file_name:
                    st.info("Select the respective labeling mode for Sepsis Patient Condition")
                    label_indicator = ["Returns to Emergency Room", "Admitted to Intensive Care",
                                       "Discharged for other Reason"]
                    _labelsel = st.radio("Labelling Indicator", label_indicator, key="radio_select_label")
                    if _labelsel == "Returns to Emergency Room":
                        parameters['label_activity'] = "Return ER"
                    elif _labelsel == "Admitted to Intensive Care":
                        parameters['label_activity'] = "Admission IC"
                    elif _labelsel == "Discharged for other Reason":
                        parameters['label_activity'] = "Release A"
                    parameters['label_check_event'] = st.number_input("Check after number of events",
                                                                      min_value=1, max_value=25, value=5,
                                                                      step=1, key="radio_number_label")
                else:
                    st.error("Label Logic for dataset is not defined")

        if parameters['folder']  != "":
            if parameters['activity'] in ['predict_next', 'pred_sfx', 'pred_log']:
                if parameters['mode'] in ['next']:
                    #   Saves the result in the URL in the Next mode
                    app_state = st.experimental_get_query_params()
                    if "my_saved_result" in app_state:
                        saved_result = app_state["my_saved_result"][0]
                        nxt_button_idx = int(saved_result)
                        # st.write("Here is your result", saved_result)
                    else:
                        #st.write("No result to display, compute a value first.")
                        nxt_button_idx = 0

                    #next_option = st.sidebar.selectbox("Type of Single Event Processing", ('Prediction of Next Event', 'Prediction of Next Events with Suffix'), key='next_dropdown_opt')
                    with st.sidebar.beta_expander('Type of Single Event Processing'):
                        st.info("Select **Execution Mode** for simulating the dashboard for the Users, **Evaluation Mode** to judge the trustworthiness of the ML model prediction")
                        next_option = st.radio('', ['Execution Mode', 'What-If Mode', 'Evaluation Mode'], key="single_event_processing")
                    #st.sidebar.markdown("""---""")

                    if next_option == 'Execution Mode':
                        next_option = 'history_with_next'
                    elif next_option == 'What-If Mode':
                        next_option = 'what_if'
                    elif next_option == 'Evaluation Mode':
                        next_option = 'next_action'
                    # Read the Test Log
                    filter_log, filter_log_columns, file_name = read_next_testlog()
                    essential_columns = ['task', 'role', 'end_timestamp']
                    extra_columns = ['caseid', 'label', 'dur', 'acc_cycle', 'daytime',
                                     'dur_norm', 'ac_index', 'rl_index', 'label_index',
                                     'wait_norm', 'user', 'open_cases_norm', 'daytime_norm',
                                     'acc_cycle'] #Add the Columns here which you don't want to display
                    display_columns = list(set(filter_log_columns) - set(essential_columns+extra_columns ))
                    filter_attr_display, filter_caseid, filter_caseid_attr_df = next_columns(filter_log, display_columns)
                    parameters['nextcaseid'] = filter_caseid

                    print("Display Attributes :", filter_attr_display.iloc[[2]])

                    st.subheader('🔦 State of the Process')
                    state_of_theprocess = st.empty()

                    parameters['multiprednum'] = num_predictions(filter_caseid_attr_df)

                    if parameters['multiprednum'] == 1:
                        variant_opt = 'arg_max'
                    elif parameters['multiprednum'] > 1:
                        variant_opt = 'multi_pred'

                    parameters['variant'] = variant_opt
                    parameters['next_mode'] = next_option

                    filter_caseid_attr_df = filter_caseid_attr_df[essential_columns].values.tolist()

                    #---Logic to select the label
                    label_identifier(file_name)


                    # --- Evaluation Mode
                    if next_option == 'next_action':
                        filter_caseid_attr_list = st.select_slider("Choose [Activity, User, Time]", options=filter_caseid_attr_df, key="caseid_attr_slider")

                        _idx = filter_caseid_attr_df.index(filter_caseid_attr_list)
                        filter_caseid_attr_list.append(_idx)

                        #Selected suffix key, Converting list to dictionary
                        filter_key_attr = ["filter_acitivity", "filter_role", "filter_time", "filter_index"]
                        filter_key_pos = [0, 1, 2, 3]
                        assert (len(filter_key_attr) == len(filter_key_pos))
                        _acc_val = 0
                        for i in range(len(filter_key_attr)):
                            filter_caseid_attr_list.insert(filter_key_pos[i] + _acc_val, filter_key_attr[i])
                            _acc_val += 1
                        filter_caseid_attr_dict = _list2dictConvert(filter_caseid_attr_list)
                        #print("Value of Slider :", filter_caseid_attr_dict)

                        #Passing the respective paramter to Parameters
                        parameters['nextcaseid_attr'] = filter_caseid_attr_dict
                        if (_idx+1) < len(filter_caseid_attr_df): #Index starts from 0 so added 1 to equate with length value
                            _filterdf = filter_attr_display.iloc[[_idx]]
                            _filterdf.index = [""] * len(_filterdf)
                            state_of_theprocess.dataframe(_filterdf)
                            st.sidebar.markdown("""---""")
                            if st.sidebar.button("Process", key='next_process'):
                                with st.spinner(text='In progress'):
                                    predictor = pr.ModelPredictor(parameters)
                                    print("predictor : ", predictor.acc)
                                st.success('Done')
                        else:
                            st.error('Reselect the Suffix to a lower Value')
                    #--- Execution Mode
                    elif next_option == 'history_with_next':
                        st.experimental_set_query_params(my_saved_caseid=filter_caseid)

                        st.sidebar.markdown("""---""")
                        next_button = st.sidebar.button("Process", key='next_process_action')

                        _filterdf = filter_attr_display.iloc[[nxt_button_idx]]
                        _filterdf.index = [""] * len(_filterdf)
                        state_of_theprocess.dataframe(_filterdf)
                        if (next_button) and ((nxt_button_idx) < len(filter_caseid_attr_df)+1):

                            nxt_button_idx += 1
                            st.experimental_set_query_params(my_saved_result=nxt_button_idx, my_saved_caseid=filter_caseid)  # Save value

                            filter_caseid_attr_list = [nxt_button_idx - 1]

                            filter_key_attr = ["filter_index"]
                            filter_key_pos = [0]
                            assert (len(filter_key_attr) == len(filter_key_pos))
                            _acc_val = 0
                            for i in range(len(filter_key_attr)):
                                filter_caseid_attr_list.insert(filter_key_pos[i] + _acc_val, filter_key_attr[i])
                                _acc_val += 1
                            filter_caseid_attr_dict = _list2dictConvert(filter_caseid_attr_list)

                            parameters['nextcaseid_attr'] = filter_caseid_attr_dict

                            with st.spinner(text='In progress'):
                                predictor = pr.ModelPredictor(parameters)
                                print("predictor : ", predictor.acc)
                            st.success('Done')
                            if (nxt_button_idx) >= len(filter_caseid_attr_df)+1:
                                #next_button.enabled = False
                                st.experimental_set_query_params(my_saved_result=0)
                                st.error('End of Current Case Id, Select the Next Case ID')
                        elif ((nxt_button_idx) >= len(filter_caseid_attr_df)+1):
                            st.experimental_set_query_params(my_saved_result=0)  # reset value
                            st.error('End of Current Case Id, Select the Next Case ID')
                    #--- What-If Mode
                    elif next_option == 'what_if':
                        form = st.form(key="my_whatif_form")
                        form.subheader("What-IF Prediction Choose Box")
                        # # --------------------------------------------------------------------------
                        # Creating prediction selection radio button
                        choose_pred_lst = ['SME']
                        for _dx in range(parameters['multiprednum']):
                            _dx += 1
                            choose_pred_lst.append("Prediction " + str(_dx))
                        st.write('<style>div.row-widget.stRadio > div{flex-direction:row;}</style>', unsafe_allow_html=True)
                        # # --------------------------------------------------------------------------
                        # with st.beta_expander('Choice of Prediction'):
                        form.info("Choose the Prediction according to which System generates the next prediction, "
                                "**SME** (Subject Matter Expert): decision solely based on users instinct and knowledge of business process about the process, "
                                "**Prediction n** : decision solely based on the respective ranked confidence of the process")
                        parameters['predchoice'] = form.radio('', choose_pred_lst, key="radio_select_whatif")
                        # # --------------------------------------------------------------------------
                        st.experimental_set_query_params(my_saved_caseid=filter_caseid)
                        st.sidebar.markdown("""---""")
                        next_button = form.form_submit_button("Process")

                        _filterdf = filter_attr_display.iloc[[nxt_button_idx]]
                        _filterdf.index = [""] * len(_filterdf)
                        state_of_theprocess.dataframe(_filterdf)
                        print("Prediction Choice : ", parameters['predchoice'])

                        if (next_button) and ((nxt_button_idx) < len(filter_caseid_attr_df)):

                            nxt_button_idx += 1

                            st.experimental_set_query_params(my_saved_result=nxt_button_idx,
                                                             my_saved_caseid=filter_caseid)  # Save value

                            filter_caseid_attr_list = [nxt_button_idx - 1]

                            filter_key_attr = ["filter_index"]
                            filter_key_pos = [0]
                            assert (len(filter_key_attr) == len(filter_key_pos))
                            _acc_val = 0
                            for i in range(len(filter_key_attr)):
                                filter_caseid_attr_list.insert(filter_key_pos[i] + _acc_val, filter_key_attr[i])
                                _acc_val += 1
                            filter_caseid_attr_dict = _list2dictConvert(filter_caseid_attr_list)

                            parameters['nextcaseid_attr'] = filter_caseid_attr_dict
                            with st.spinner(text='In progress'):
                                predictor = pr.ModelPredictor(parameters)
                                print("predictor : ", predictor.acc)
                            st.success('Done')
                            if (nxt_button_idx) >= len(filter_caseid_attr_df):
                                # next_button.enabled = False
                                st.experimental_set_query_params(my_saved_result=0)
                                st.error('End of Current Case Id, Select the Next Case ID')
                        elif ((nxt_button_idx) >= len(filter_caseid_attr_df)):
                            st.experimental_set_query_params(my_saved_result=0)  # reset value
                            st.error('End of Current Case Id, Select the Next Case ID')

                elif parameters['mode'] in ['batch']:
                    parameters['multiprednum'] = 3  # Change here for batch mode Prediction
                    with st.sidebar.beta_expander('Variant'):
                        st.info("Select **Max Probability** for the most probable events,"
                                " **Multiple Prediction** for the prediction of the multiple events, "
                                "and **Random Prediction** for prediction of random recommendation of events")
                        variant_opt = st.sidebar.selectbox("", (
                        'Max Probability', 'Multiple Prediction', 'Random Prediction'),
                                                           key='variant_opt')
                    #st.sidebar.markdown("""---""")

                    if variant_opt == 'Max Probability':
                        variant_opt = 'arg_max'
                    elif variant_opt == 'Multiple Prediction':
                        variant_opt = 'multi_pred'
                    elif variant_opt == 'Random Prediction':
                        variant_opt = 'random_choice'
                    parameters['variant'] = variant_opt  # random_choice, arg_max for variants and repetitions to be tested
                    parameters['next_mode'] = ''
                    parameters['predchoice'] = ''
                    st.sidebar.markdown("""---""")
                    if st.sidebar.button("Process", key='batch_process'):
                        print(parameters)
                        print(parameters['folder'])
                        print(parameters['model_file'])
                        start = time.time()

                        with st.spinner(text='In progress'):
                            predictor = pr.ModelPredictor(parameters)
                        end = time.time()
                        st.success('Done')
                        print("Elapsed Time : ", end - start)

if __name__ == "__main__":
    main(sys.argv[1:])


#streamlit run dashboard.py