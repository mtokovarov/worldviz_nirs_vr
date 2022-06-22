import viz
import vizcam
import vizconnect
import viztask


def run_experiment():
    init_experiment()
    show_initial_instruction()
    run_training()
    run_blocks()
    
def init_experiment():
	print('init_experiment function')
	
def show_initial_instruction():
	print('show_initial_instruction function')
	
def run_training():
	print('run_training function')
	
def run_blocks():
	print('run_blocks function')


model = viz.addChild('dojo.osgb')
viz.setMultiSample(8)
viz.fov(60)
vizconnect.go('example_HTC_preset.py')
viztask.schedule(run_experiment)

