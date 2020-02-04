# pynuXmv

`pynuXmv` is a small utility capable of transpiling a subset of [Python](https://www.python.org/) to [`nuXmv`](https://nuxmv.fbk.eu/) specification code.

## Installation

`pynuXmv` requires `nuXmv` 2.0.0 (but should work with any version `>= 2.0.0`) and `python >=3.8`.

To install it,

	pip install pynuxmv
	
	
	
## Execution

From a shell, launch:

	pynuXmv <python_fname> <nuxmv_out_fname>
	
This will transpile `python_fname` and save the result into `nuxmv_out_fname`.



## Examples

See `tests/` folder for examples. 

A simple one:

	from pynuxmv.main import *

	a = 0
	b = 0
	while (a + b < 2):
	  if b == 0 and a == 1:
		b = 1  
	  else:
		if b == 1 and a == 1:
		  b = 0  
	  if a == 1:
		a = 0
	  else:
		a = 1

	ltlspec("F (a = 1 & b = 1)")
	ltlspec("(a = 0 & b = 0) -> F (a = 1 & b = 0)")
	ltlspec("(a = 1 & b = 0) -> F (a = 0 & b = 1)")
	ltlspec("(a = 0 & b = 1) -> F (a = 1 & b = 1)")

is converted into:

	MODULE main

	VAR
	a: integer;
	b: integer;
	line: integer;

	ASSIGN
	init(a) := 0;
	init(b) := 0;
	init(line) := 1;

	next(line) := case
		line = 8 & b = 1 & a = 1: line + 1; -- if(True)
		line = 8: 11;                       -- if(False)
		line = 5 & b = 0 & a = 1: line + 1; -- if(True)
		line = 6: 12; -- end if(True) 
		line = 5: 8;  -- else
		line = 12 & a = 1: line + 1; -- if(True)
		line = 13: 17;               -- end if(True) 
		line = 12: 15;               -- else
		line = 4 & a + b < 2: line + 1; -- while(True)
		line = 4:  18; -- while(False)
		line = 17: 4;  -- loop while
		line = 21: 21; 
		TRUE: line + 1; 
	esac;

	next(a) := case
		line = 13: 0;
		line = 15: 1;
		TRUE: a; 
	esac;

	next(b) := case
		line = 6: 1;
		line = 9: 0;
		TRUE: b; 
	esac;

	LTLSPEC F (a = 1 & b = 1);
	LTLSPEC (a = 0 & b = 0) -> F (a = 1 & b = 0);
	LTLSPEC (a = 1 & b = 0) -> F (a = 0 & b = 1);
	LTLSPEC (a = 0 & b = 1) -> F (a = 1 & b = 1);
	
This nuXmv file can be run with:

	nuXmv -source cmd_ltl <filename>
	
where `cmd_ltl` (or, for invariant checking, the equivalent `cmd_invar`) can be found in this repository.


## Limitations

Up to now, this simple script has many limitations:

+ No support for `for` construct
+ No support for types other than `integer` (no bounded integer, no words, no bitvectors, no arrays)
+ No support for higher structures (i.e. function calls, classes...)
+ No support for concurrent execution and/or `nuXmv` modules

It's not (it shouldn't) be difficult to implement some of these things, but it will take some time to do it.
