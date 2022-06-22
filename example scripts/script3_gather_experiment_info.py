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

#global variables
EXPERIMENT_START = 0
LEFT_CONTROLLER = 0
RIGHT_CONTROLLER = 0
PATIENT_NAME =''
RECORD_FILE_NAME = '' 
IP = ''
IS_WITH_HTTP = False


def run_experiment():
    yield init_experiment()
    show_initial_instruction()
    run_training()
    run_blocks()
    

def show_initial_instruction():
	print('show_initial_instruction function')
	
def run_training():
	print('run_training function')
	
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
    experiment_start = datetime.datetime.utcnow()

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

model = viz.addChild('dojo.osgb')
viz.setMultiSample(8)
viz.fov(60)
vizconnect.go('example_HTC_preset.py')
viztask.schedule(run_experiment)