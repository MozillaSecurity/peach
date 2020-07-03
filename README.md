![Logo](https://github.com/posidron/posidron.github.io/raw/master/static/images/peach.png)

MozPeach is a fork of [Peach v2.7](http://www.peachfuzzer.com) by Mozilla Security. With support from our community and partnerships our goal is to continue to deliver Peach as an open source product with Python compatibility and new features.

Our focus is on usability, speed and fewer dependencies. We have also begun work on Python 3 support, replaced deprecated Python dependencies, switched the XML back-end, added a new configuration system, simplified code and much more.

### Setup

##### Prerequisites for Ubuntu
```
sudo apt-get --yes --quiet install libxml2-dev libxslt1-dev lib32z1-dev
```

##### General
```bash
pip install virtualenv
pip install virtualenvwrapper

git clone --depth 1 https://github.com/mozillasecurity/peach

cd peach
git clone --depth 1 https://github.com/mozillasecurity/fuzzdata

mkvirtualenv -r requirements.txt peach
```

or

```bash
workon peach
```

### Fundamentals
Peach uses XML based "pits" as configuration files. There are two types of pits which we will briefly describe here.

**Pit: Data Model**

A data-model pit is an XML description of a specification and is required to parse any kind of input into an in-memory XML tree. Peach then uses that tree to generate fuzzed output.

**Pit: Target**

The target pit is used to define how the target process will get fuzzed, how it will be monitored for suspicious behavior and how to deal with results.

It is optional whether you place everything into one pit however not doing so will simplify working with multiple targets, different hosts and reusing pits. Following the data model/target pit practice will allow the reuse of data model pits across projects.


### Examples

##### Run
```bash
./peach.py -pit Pits/<component>/<format>/<name>.xml -target Pits/Targets/firefox.xml -run Browser
```

**HINT**: You can set related configuration values for both pits from the command-line by using the -macros switch.

##### Debug
```bash
./peach.py -pit Pits/<component>/<format>/<name>.xml -1 -debug | less -R
```

**NOTE**: This will show a very verbose output of the parsing process. To see only the results of the parsing process for each element you can add: "| grep Rating | less -R"


### Help Menu
```
% ./peach.py -h
usage: peach.py [-h] [-pit path] [-run name]
                [-analyzer ANALYZER [ANALYZER ...]] [-parser PARSER]
                [-target TARGET] [-macros MACROS [MACROS ...]] [-seed #]
                [-debug] [-new] [-1] [-range # #] [-test] [-count] [-skipto #]
                [-parallel # #] [-agent # #] [-logging #]
                [-check model samples] [-verbose] [-clean] [-version]

Peach Runtime

optional arguments:
  -h, --help            show this help message and exit
  -pit path             pit file
  -run name             run name
  -analyzer ANALYZER [ANALYZER ...]
                        load analyzer.
  -parser PARSER        use specific parser.
  -target TARGET        select a target pit.
  -macros MACROS [MACROS ...]
                        override configuration macros
  -seed #               seed
  -debug                turn on debugging. (default: False)
  -new                  use new relations.
  -1                    run single test case.
  -range # #            run range of test cases.
  -test                 validate pit file.
  -count                count test cases for deterministic strategies.
  -skipto #             skip to a test case number.
  -parallel # #         use parallelism.
  -agent # #            start agent.
  -logging #            verbosity level of logging
  -check model samples  validate a data model against a set of samples.
  -verbose              turn verbosity on. (default: False)
  -clean                remove python object files.
  -version              show program's version number and exit
```

### Resources

Resources which aid in building a pit based on the grammar of a file format:

    * http://www.sweetscape.com/010editor/templates/
    * http://www.synalysis.net/formats.xml
