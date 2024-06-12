# CUBEMELTER
A Tkinter GUI app for interacting with the Drive Test Load sled and monitoring cube supply info


## Dependencies
* Python 3.6+
* Tkinter
* Spectracan
* [PyInstaller](https://pyinstaller.readthedocs.io/en/stable/) (for bundling into single executable, dev only)

To install the dependencies setup your venv and use
```
pip install -r requirements.txt -i http://sustaining:suseng145@waterworks:8809 --trusted-host waterworks
```

If developing in Ubuntu tkinter is not included in the python3 package, you will have to additionally install python3-tk

## Building an exe for the application
This will have to done on the platform it is intended to run on. (Only tested on windows)

`pyinstaller` will be used to build a native executable bundle out of the application \
Run the following command to build this
```
pyinstaller --noconfirm --clean --add-data="icon.ico;." --icon "icon.ico" --onefile "cube_melter.py"
```

After creating the executable, you'll find it in the created `dist` folder. 
