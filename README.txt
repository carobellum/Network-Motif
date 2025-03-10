This is the documentation for the FinalMotif.py module:

FinalMotif.py Functions:

Overview: FinalMotif.py is essentially a wrapper for a simple C++ program (Kavosh) for calculating the total number of motifs in a given graph. Kavosh takes in an edge list of the graph and ouputs a txt file with the number of each motif found. We used cPickle to store the raw data as a python dictionary. Since the runtime of this code increases exponentially with motif size, I created a cache directory that stores the motif results in the json format.

MotifData:
	This class contains the motif data for a set of graphs. It is the returned value for the findMotifs() function. It is basically a wrapper for a list of dictionaries. Each element in the list is represents 1 patient and the dictionary maps motif ID to the number of that motif found in the graph. It contains various access functions to iterate through or retrieve various motif data.

makeSwapData(degree=10):
	This crates a pkl file that contains the graphs of the original data after undergoing edge swapping
	"degree" is the average degree you want to threshold the graph with.
	
buildCache(motifSize, degree):
	This function builds the cache of both original graphs and edge-swapped ones for faster processing in future runs of findMotifs
	"motifSize" is the size of the motif you want to calculate.
	"degree" is the average degree you want to threshold the graph with.

findMotifs(data,key,motifSize=3,degree=10,randGraphs=None, useCache=True):
	This is the main motif finding routine.
	"data" is a dictionary of all the graph data.
	"key" is the key into the dictionary for which you want to run findMotifs on.
	"motifSize" is the size of the motif you want to calculate.
	"degree" is the average degree you want to threshold the graph with.
	"randGraphs" is an optional argument that can be set to random set of random graph data to be used instead of the data from the "data" argument.
	"useCache" if True, looks first in the cache when running this function to see if the result has already been computed. If not, it computes the motifs and saves the results in the cache for late use.
	This function returns a MotifData object containing all the results

convertIDToGraph(mid, motifSize, save=False):
	This function draws a graph of the given motif ID
	"mid" is the motif ID you want to draw
	"motifSize" is the size of the motif for the ID
	"save" if true saves the picture in png format. If false, just displays a picture of the graph


plotMotifGraphs(data,motifSize=3,degree=10,numofmotifs=10,usetotal=False):
	This function plots a pyplot graph of the data


PDFstats(data, filename, edgeSwap=False, motifSize=3, degree=10):
	Creates a latex document of the T-test data for the motif distribution probabilities
	"filename" name of outputfile
	"edgeSwap" is whether to use edge swapped graphs for the RAND group.
	"motifSize" is the size of the motif you want to calculate.
	"degree" is the average degree you want to threshold the graph with.

PDFdiststats(data, filename, edgeSwap=False, motifSize=3, degree=10):
	Same as above except it creates a latex document of the T-test data

