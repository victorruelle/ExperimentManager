from utils import get_options

d = { 
	"name" : "Julie",
	"value" : 1,
	"details" : {
		"age" : 22,
		"towns" : {
			0 : "Brussels",
			1 : "Paris"
			}
		}	
	}
	
prefixes = ['details.towns','details.age']

print(get_options(d,prefixes = prefixes))