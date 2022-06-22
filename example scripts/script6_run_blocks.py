#vizard modules
import viz
import vizcam
import vizconnect
import viztask
import steamvr
import vizact
import vexptoolbox as vx

#general purpose modules
import datetime
import numpy as np
from threading import Thread
import pandas as pd
import os
import requests
import random

#global variables
EXPERIMENT_START = 0
LEFT_CONTROLLER = 0
RIGHT_CONTROLLER = 0
PATIENT_NAME =''
RECORD_FILE_NAME = '' 
IP = ''
IS_WITH_HTTP = False
TRAINING_TRIAL_CNT = 30
TOTAL_TRIAL_TIME = 1.0
FLANKER_SIZE_SCALER = 0.3
PULSE_TIME = 0.01
INTER_PULSE_TIME = 0.18
PULSE_CNT = 2
REST_TIME = 21

CONGRUENT_DISTRACTOR = 1
INCONGRUENT_DISTRACTOR = 2
NEUTRAL_DISTRACTOR = 3
RELAX = 4
STR_TO_HTTP_CODE_DICT = {
                    'congruent_distractor':CONGRUENT_DISTRACTOR,
                    'incongruent_distractor':INCONGRUENT_DISTRACTOR,
                    'neutral_distractor':NEUTRAL_DISTRACTOR,
                    'relax':RELAX
                    }
BLOCK_STRUCTURE_FOLDER_PATH = 'block_config_single_taks_flanker'
TARGET_FILE_PATH = 'records'
GROUP_NUMBER = 1
BLOCK_SET_IN_GROUP_NUMBER = 2
TRAINING_TRIAL_CNT = 30

def run_experiment():
    yield init_experiment()
    yield show_initial_instruction()
    yield run_training()
    yield run_blocks()

def run_blocks():
	print('run_blocks function')

##########Function and subfunctions of 
########          init_experiment
def init_experiment():
	init_experiment_start_time()
	init_view_point_reset()
	init_controllers() 
	yield gather_experiment_info()

def init_experiment_start_time():
    global EXPERIMENT_START
    EXPERIMENT_START = datetime.datetime.utcnow()

def init_view_point_reset():
    oriMode = vizconnect.VIEWPOINT_MATCH_DISPLAY
    posMode = vizconnect.VIEWPOINT_MATCH_FEET
    # Add a vizconnect viewpoint.
    vp = vizconnect.addViewpoint(   pos=[0,0,0],
                                    euler=[0, 0, 0],
                                    posMode=posMode,
                                    oriMode=oriMode,
    )
    vp.add(vizconnect.getDisplay())
    vizconnect.resetViewpoints()
    # add a reset key so when r is pressed the user is moved back to the viewpoint
    vizact.onkeydown('r', vizconnect.resetViewpoints)
 
def init_controllers():
    global LEFT_CONTROLLER, RIGHT_CONTROLLER
    controllers = steamvr.getControllerList()
    if len(controllers) < 2:
        raise('Not all controllers connected')
    if controllers[0]._vizconnectName == 'l_hand_input':
        LEFT_CONTROLLER = controllers[0]
        RIGHT_CONTROLLER = controllers[1]
    else:
        LEFT_CONTROLLER = controllers[1]
        RIGHT_CONTROLLER = controllers[0]

def gather_experiment_info():
    global PATIENT_NAME,  RECORD_FILE_NAME, IP, IS_WITH_HTTP
    questions = ['IP']
    PATIENT_NAME, gender, age, EXPERIMENT_NAME, IP = yield from get_participant_data(questions)
    RECORD_FILE_NAME = f'PATIENT_{PATIENT_NAME}_{gender}_{age}_sess_{EXPERIMENT_NAME}_{datetime.datetime.utcnow().strftime("%Y-%m-%d %H.%M.%S")}'
    IS_WITH_HTTP = not IP == '' 

def get_participant_data(questions = []):
    ex = vx.Experiment(name='Example',
                   debug=False, 
                   auto_save=False)
    yield ex.requestParticipantData(questions = questions)
    return ex.participant.id, ex.participant.gender, ex.participant.age, ex.participant.session, ex.participant.IP

##########Function and subfunctions of 
########          show_initial_instruction

def show_initial_instruction():
    instructions = """
                    You are taking a part in an experiment, read the instructions carefully.
                    1. The stimuli will be shown in the form of the following symbols:
                    
                         < < < < < < <, > > > < > > >, > > > > > > >, < < < > < < <.
                    
                    2. When you feel the wibration of the controllers, you have to answer
                    specifying the direction of the central symbol of the shown stimulus 
                    by pressing the trigger of correspondent joystick.
                    
                    For the above example the results fould be:
                    < (left), < (left), > (right), > (right)

                    3. That's it! Press right joystick trigger to start the training session."""
    yield vx.waitVRInstruction(instructions, controller=RIGHT_CONTROLLER, title = 'Instruction')

	
##########Function and subfunctions of 
########          run_training
def run_training():
    for _ in range(TRAINING_TRIAL_CNT):
        trial = get_random_trial()
        results = yield from run_trial(trial)
        yield show_feedback(trial, results)
    
def get_random_trial():
    flanker_type = np.random.choice(['left', 'right'],size = 1)[0]
    distraction_congruencity = np.random.choice(['neutral', 'congruent', 'incongruent'],size = 1)[0]
    flanker_congruencity = np.random.choice(['congruent', 'incongruent'],size = 1)[0]
    
    return {'flanker_type': flanker_type,
            'distraction_congruencity': distraction_congruencity, 
            'flanker_congruencity': flanker_congruencity}

def show_feedback(trial, results):
    message = ''
    if results['response_provided'] is None:
        message += 'Too long!\n'
    elif results['response_provided'] == trial['flanker_type']:
        message += 'Correct  answer!\n'
    else:
        message += 'Wrong  answer!\n'
    message += 'Press any key to continue!'
    yield show_message_waiting_for_button(message)


def run_trial(trial):
    response_provided = None
    response_time = None
    is_correct = None
    stimulus = flanker_show_stimulus(trial['flanker_type'],
                                      trial['flanker_congruencity'])
    
    def on_response_provided(event):
        nonlocal response_time, response_provided, stimulus, is_correct

        response_time = (get_time_from_experiment_start() - start_time).total_seconds()
        if event.object == LEFT_CONTROLLER:
            response_provided = 'left'
        if event.object == RIGHT_CONTROLLER:
            response_provided = 'right'
        is_correct = trial['flanker_type']==response_provided
        stimulus.visible(viz.OFF)
            
    viz.callback(viz.SENSOR_DOWN_EVENT,on_response_provided)
    start_time = get_time_from_experiment_start()
    
    
    run_distraction(trial['flanker_type'], 
                    trial['distraction_congruencity'])
    yield viztask.waitTime(TOTAL_TRIAL_TIME)
    stimulus.remove()
    viz.callback(viz.SENSOR_DOWN_EVENT,None)
    
    return make_dict_of_args(response_provided=response_provided,
                            trial_start_time = start_time.total_seconds(), response_time = response_time,
                            is_correct = is_correct)
    
def pulse_vibration(controllers):    
    def func():
        for i in range(PULSE_CNT):
            for controller in controllers:
                controller.setVibration(PULSE_TIME, amplitude=1)
            viz.waitTime(PULSE_TIME)
            viz.waitTime(INTER_PULSE_TIME)
    Thread(target = func).start()
    
def flanker_show_stimulus(flanker_type, flanker_congruencity):
    message = get_stimulus_str(flanker_type, flanker_congruencity)
    return show_message_on_fixed_position_with_random_shift(message, size_scaler = FLANKER_SIZE_SCALER,
                                                shift_val = 0.5, color = (0.53,0.81,0.92))


def get_stimulus_str(flanker_type, congruent):
    flanker_dict = {
                    ('left', 'congruent'): '< < < < < < <',
                    ('left', 'incongruent'): '> > > < > > >',
                    ('right', 'congruent'): '> > > > > > >',
                    ('right', 'incongruent'): '< < < > < < <',
                    ('left', 'neutral'):'= = = < = = =',
                    ('right', 'neutral'):'= = = > = = ='
    }
    return flanker_dict[(flanker_type, congruent)]

def run_distraction(flanker_type, distraction_congruencity):
    controllers = get_controllers_for_distraction(flanker_type, distraction_congruencity)
    pulse_vibration(controllers)
    
    
def get_controllers_for_distraction(flanker_type, distraction_congruencity):
    controller_distract_dict = {
                    ('left', 'congruent'): [LEFT_CONTROLLER],
                    ('left', 'incongruent'): [RIGHT_CONTROLLER],
                    ('right', 'congruent'): [RIGHT_CONTROLLER],
                    ('right', 'incongruent'): [LEFT_CONTROLLER],
                    ('left', 'neutral'): [LEFT_CONTROLLER, RIGHT_CONTROLLER],
                    ('right', 'neutral'):[LEFT_CONTROLLER, RIGHT_CONTROLLER]
    }
    return controller_distract_dict[(flanker_type, distraction_congruencity)]

##########Function and subfunctions of 
########          run_blocks
def run_blocks():
    yield show_message_waiting_for_button(
                "Press any button, when you are ready for the experiment")
    if IS_WITH_HTTP:
        send_start_record()
        
    #yield run_rest_phase(REST_TIME)
    trial_blocks = get_trial_block_data()
    for i in range(GROUP_NUMBER):
        random.shuffle(trial_blocks)
        for block in trial_blocks:
            if IS_WITH_HTTP:
                send_marker(block['name'])
            random.shuffle(block['data'])
            for trial in block['data']:
                result = yield from run_trial(trial)
                log_feedback_in_thread(({'block': block['name'], **trial, **result},))            
            yield run_rest_phase(REST_TIME)

def get_trial_block_data():
    block_set, block_names = read_block_data()
    group_of_trial_blocks = block_set*BLOCK_SET_IN_GROUP_NUMBER
    group_of_trial_block_names = block_names*BLOCK_SET_IN_GROUP_NUMBER
    trial_blocks = [{'name':n, 'data': b} for n, b in zip(group_of_trial_block_names, group_of_trial_blocks)]
    return trial_blocks
    
def read_block_data():
    block_files = os.listdir(BLOCK_STRUCTURE_FOLDER_PATH)
    blocks = []
    block_names = []
    for block_file in block_files:
        data = pd.read_csv(f'{BLOCK_STRUCTURE_FOLDER_PATH}//{block_file}', sep = ',')
        columns = data.columns.to_list()
        data = [{col:val for col, val in zip(columns, row)} for row in data.values]
        blocks.append(data)
        block_names.append(block_file.split('.')[0])
    return blocks, block_names
    
def run_rest_phase(rest_time):
    if IS_WITH_HTTP:
        send_marker('relax')
    last_seconds = 5
    text = show_message_on_fixed_position('Relax...')
    yield viztask.waitTime(rest_time-last_seconds-2)
    text.remove()
    for i in range(last_seconds):
        message = f'The rest phase will be over in {last_seconds - i} seconds'
        text = show_message_on_fixed_position(message)
        yield viztask.waitTime(1)
        text.remove()
    text = show_message_on_fixed_position('Action!')
    yield viztask.waitTime(1)
    text.remove()
    yield viztask.waitTime(1)
    
def log_feedback(feedback):
    global logging_started
    pd_data = pd.DataFrame(feedback, index=[0])
    path = f'{TARGET_FILE_PATH}\\{RECORD_FILE_NAME}.csv'
    if not os.path.exists(path) or not logging_started:
        pd_data.to_csv(path, mode='w', index=False, header=True, sep = ';')
        logging_started = True
    else:
        pd_data.to_csv(path, mode='a', index=False, header=False, sep = ';')

def log_feedback_in_thread(kwargs):
    run_in_thread(log_feedback, kwargs)


########################################################################
#######Utility functions, that contain actions, repeating in the code
def get_time_from_experiment_start():
    return datetime.datetime.utcnow() - EXPERIMENT_START
    
def make_dict_of_args(**kwargs):
     body = kwargs
     return body

def show_text(text, pos, color = None, angle = 0, size_scaler = 0.5,
              backdrop_offset = 0.07):
    text_2d = viz.addText(text,pos=pos)
    text_2d.font('Calibri') 
    text_2d.alignment( viz.ALIGN_CENTER_BASE ) 
    #Set text font size and resolution (from 0 to 1).
    text_2d.fontSize(size_scaler) 
    text_2d.resolution(1)        
    text_2d.setEuler(angle)
    if (color is not None):
        text_2d.color(color)
    text_2d.setBackdrop(viz.BACKDROP_OUTLINE)
    text_2d.disable(viz.LIGHTING)
    text_2d.setBackdropOffset(backdrop_offset)
    return text_2d

def show_message_on_fixed_position(message, text_pos = [0,1.8,6.4], size_scaler = 0.3, color = viz.WHITE):
    return show_text(message, text_pos, color, size_scaler = size_scaler)   
    
def show_message_on_fixed_position_with_random_shift(message, text_pos = [0,1.8,6.4], size_scaler = 0.3,
                shift_val = 0.1, color = viz.WHITE):
    pos = [tp+(np.random.rand() - 0.5)*2*shift_val for tp in text_pos[:-1]] + [text_pos[-1]]
    return show_message_on_fixed_position(message, pos, size_scaler = size_scaler, color = color)   
    
def show_message_waiting_for_event(message, event_id, text_pos = [0,1.8,6.4], angle = 0, scaler = 0.3):
    text = show_message_on_fixed_position(message, text_pos,size_scaler = scaler)
    text.setEuler(angle)
    yield viztask.waitEvent(event_id)
    text.remove()
    
def show_message_in_front_of_avatar_waiting_for_event(message, event_id):
    angle = viz.MainView.getEuler()[0]
    x,y,z = viz.MainView.getPosition()  
    x = x + math.sin(viz.radians(angle))*DISTANCE_TO_FLANKER_STIMULUS*0.9
    z = z + math.cos(viz.radians(angle))*DISTANCE_TO_FLANKER_STIMULUS*0.9
    text_pos = [x,y,z]
    yield show_message_waiting_for_event(message, event_id, text_pos, angle)
    
def show_message_waiting_for_button(message):
    yield show_message_waiting_for_event(message, viz.SENSOR_DOWN_EVENT)
    
def run_in_thread(func, args = ()):
    func_lambda = lambda : func(*args)
    thread = Thread(target = func_lambda)
    thread.start()

def send_marker(marker):
    requests.post(f'{IP}/toggleMarker?id={STR_TO_HTTP_CODE_DICT[marker]}')
def send_start_record():
    requests.post(f'{IP}/startRecord?filename={EXPERIMENT_NAME}_{PATIENT_NAME}')
def send_stop_record():
    requests.post(f'{IP}/stopRecord')


model = viz.addChild('dojo.osgb')
viz.setMultiSample(8)
viz.fov(60)
vizconnect.go('example_HTC_preset.py')
viztask.schedule(run_experiment)