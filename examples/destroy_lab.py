from labmachine.shortcuts import load_jupyter
j = load_jupyter("state.json")
j.destroy_lab()
j.save("state.json")
