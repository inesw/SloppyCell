import sets, copy, os

class ExperimentCollection(dict):
    """
    ExperimentCollection(experiment name list)

    An ExperimentCollection unites a collection of experiments. For now, it's
    most important function is to collect group the independent variables by
    Calculation to avoid wasting computer effort redoing calculations.

    Individual experiments can be accessed via dictionary-type indexing.
    """
    def __init__(self, exptList = []):
        for expt in exptList:
            self.AddExperiment(expt)

    def AddExperiment(self, expt):
        """
        LoadExperiments(experiment name list)

        Adds the experiments in the list to the collection
        """
        if expt.GetName() in self:
            raise ValueError, "Experiment already has name %s" % str(expt.GetName())

        self[expt.GetName()] = expt

    def GetVarsByCalc(self):
        """
        GetIndVarsByCalc() -> dictionary

        Returns a dictionary of all the dependent and independent variables for 
        all the calculations required to compare with the data in all the
        experiments. The dictionary is of the form: 
         dictionary(calculation name) -> ordered list of unique independent
                                         variables
        """
        varsByCalc = {}
        for expt in self.values():
            data = expt.GetData()

            for calc in data:
                varsByCalc.setdefault(calc, {})
                for depVar in data[calc]:
                    # Using a set is a convenient way to make sure
                    # independent variables aren't repeated
                    varsByCalc[calc].setdefault(depVar, sets.Set())
                    varsByCalc[calc][depVar].union_update(data[calc]\
                                                          [depVar].keys())

        # But I convert the sets back to sorted lists before returning
        for calc in varsByCalc:
            for depVar in varsByCalc[calc]:
                varsByCalc[calc][depVar] = list(varsByCalc[calc][depVar])
                varsByCalc[calc][depVar].sort()

        return varsByCalc

    def GetData(self):
        """
        GetData() -> dictionary

        Returns a dictionary containing all the data for the experiments. The
        dictionary is of the form:
         dictionary[expt name][calc name][dependent vars][independent vars]
                 = value.

        Note that value may be an arbitrary object.
        """

        data = {}
        for exptName, expt in self.items():
            data[exptName] = expt.GetData()
        
        return data

class Experiment:
    def __init__(self, name = '', data = {}, fixedScaleFactors = {},
                 longName = ''):
        self.SetName(name)
        self.SetData(data)
        self.SetFixedScaleFactors(fixedScaleFactors)

    def SetName(self, name):
        self.name = name

    def GetName(self):
        return self.name

    def SetData(self, data):
        self.data = copy.copy(data)

    def UpdateData(self, newData):
        self.data.update(newData)

    def GetData(self):
        return self.data

    def SetFixedScaleFactors(self, fixedScaleFactors):
        self.fixedScaleFactors = fixedScaleFactors

    def GetFixedScaleFactors(self):
        return self.fixedScaleFactors

class CalculationCollection(dict):
    """
    CalculationCollection(calculation name list)

    An CalculationCollection unites a collection of calculations. It is
    responsible for generating a master list of parameters and passing each
    Calculation its appropriate parameters.

    Individual calculations can be accessed via dictionary-type indexing.
    
    XXX: Note that the parameter shuffling has not been extensively tested.
    """

    def __init__(self, calcList = []):
        self.params = KeyedList()
        for calc in calcList:
            self.AddCalculation(calc)

    def AddCalculation(self, calc):
        """
        LoadCalculations(calculations name list)

        Adds the calculations in the list to the collection and adds their
        parameters to the parameterSet
        """
        if calc.GetName() in self:
            raise ValueError, "Calculation already has name %s" % str(calc.GetName())

        self[calc.GetName()] = calc 
        for pName, pValue in calc.GetParameters().items():
            self.params.setdefault(pName, pValue)

    def GetResults(self, requestedByCalc):
        """
        GetResultsByCalc(requestedByCalc, params) -> dictionary

        Given requestedByCalc, a dictionary of the form:
         dict[calc name][dep var][ind var], and a set of parameters
        (dictionary or appropriately ordered list), returns a dictionary of
        results. The dictionary is of the form:
         dictionary[calculation][dependent variables][independent variable]
          -> result
        """
        calcVals = {}
        for (calcName, requested) in requestedByCalc.items():
            calcVals[calcName] = self[calcName].GetResult(requested)

        return calcVals

    def Calculate(self, varsByCalc, params = None):
        if params is not None:
            self.params.update(params)
	
        for (calcName, vars) in varsByCalc.items():
            self[calcName].Calculate(varsByCalc[calcName], self.params)

    def GetSensitivityResults(self, requestedByCalc):
        """
        Given requestedByCalc, a dictionary of the form:
         dict[calc name][dep var][ind var], and a set of parameters
        (dictionary or appropriately ordered list), returns a dictionary of
        results. The dictionary is of the form:
         dictionary[calculation][dependent variables][independent variable]
	 [parameter]
          -> result
        """
        calcSensVals = {}
        for (calcName, requested) in requestedByCalc.items():
            calcSensVals[calcName] = self[calcName].GetSensitivityResult(requested)

        return calcSensVals


    def CalculateSensitivity(self, varsByCalc, params = None):
        if params is not None :
            self.params.update(params)
		
        for (calcName, vars) in varsByCalc.items():
            calcPOrder = self[calcName].GetParameters().keys()
            self[calcName].CalculateSensitivity(varsByCalc[calcName], self.params)

    def GetParameters(self):
        """
        GetParameterNamesInOrder() -> list

        Returns a list of parameter names, in the order they would be expected
        if a list of values were passed in.
        """
        return self.params

class KeyedList(list):
    def __init__(self, arg1 = None):
        # We stored both a dictionary mapping keys to indices and a list of
        #  keys for efficiency
        self.keyToIndex = {}
        self.storedKeys = []

        if hasattr(arg1, 'items'):
            items = arg1.items()
        else:
            items = arg1

        if items is not None:
            for (key, value) in items:
                self.setByKey(key, value)

    def setOrder(self, order):
        if len(order) != len(self):
            raise ValueError, 'New order is of a different length!'

        oldOrder = copy.copy(self.keyToIndex)
        oldValues = copy.copy(self.values())
        self.storedKeys = []
        for (index, key) in enumerate(order):
            self.keyToIndex[key] = index
            self.storedKeys.append(key)
            self[index] = oldValues[oldOrder[key]]

    def reverse(self):
        self.setOrder(self.keys()[::-1])

    def __delitem__(self, index):
        list.__delitem__(self, index)
        del self.storedKeys[index]
        for key, ii in self.keyToIndex.items():
            if ii > index:
                self.keyToIndex[key] -= 1
            elif ii == index:
                del self.keyToIndex[key]

    def __delslice__(self, start, stop):
        # XXX: Not sure of behavior here
        if stop > len(self):
            stop = len(self)

        for index in range(start, stop)[::-1]:
            del self[index]

    def __copy__(self):
        return KeyedList(self.items())

    def __deepcopy__(self, memo):
        # XXX: Not handling recursion here
        return KeyedList(copy.deepcopy(self.items()))

    #
    # Methods for manipulating by key.
    #
    def setByKey(self, key, value):
        if key in self.storedKeys:
            self[self.keyToIndex[key]] = value
        else:
            list.append(self, value)
            self.storedKeys.append(key)
            self.keyToIndex[key] = len(self)-1

    def indexByKey(self, key):
        return self.keyToIndex[key]

    def removeByKey(self, key):
        del self[self.keyToIndex[key]]

    def getByKey(self, key, default = None):
        try:
            return self[self.keyToIndex[key]]
        except KeyError:
            if default is not None:
                return default
            else:
                raise KeyError, key

    def keys(self):
        return self.storedKeys

    def update(self, other):
        if isinstance(other, dict) or isinstance(other, KeyedList):
            for key, value in other.items():
                self.setByKey(key, value)
        else:
            if(len(self) != len(other)):
                raise ValueError, 'Other list not of same length!'
            for ii in range(len(self)):
                self[ii] = other[ii]

    def has_key(self, key):
        return (key in self.storedKeys)

    def setdefault(self, key, default=None):
        if key not in self.storedKeys:
            self.setByKey(key, default)

    def values(self):
        return self[:]

    def items(self):
        return zip(self.keys(), self.values())

    def __repr__(self):
        return 'KeyedList(%s)' % repr(self.items())

    def __str__(self):
        return os.linesep.join(['['] + 
                               [str(tup) + ',' for tup in self.items()] + [']'])

    #
    # list methods not supported
    #
    def  __add__(self, other):
        raise NotImplementedError
    def __iadd__(self, other):
        raise NotImplementedError
    def __imul__(self, factor):
        raise NotImplementedError
    def __mul__(self, factor):
        raise NotImplementedError
    def  __rmul__(self, factor):
        raise NotImplementedError
    def append(self, item):
        raise NotImplementedError
    def extend(self, other):
        raise NotImplementedError
    def insert(self, other):
        raise NotImplementedError
    def pop(self, other):
        raise NotImplementedError
    def remove(self, other):
        raise NotImplementedError
    def sort(self):
        raise NotImplementedError
