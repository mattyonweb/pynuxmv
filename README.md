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

+ Limited support for `for` construct (only with numeric `range()`s)
+ No support for types other than `integer` and `boolean` (no bounded integer, no words, no bitvectors, no arrays)
+ No support for higher structures (i.e. function calls, classes...)
+ No support for concurrent execution and/or `nuXmv` modules

It's not (it shouldn't) be difficult to implement some of these things, but it will take some time to do it.

Also, take a look at the `TODO.md` file for other thing that can (not) be done up to now.

___

## Basic tutorial

The following assumes that you are examining a portion of "self-contained" code (ie. code that doesn't reference variables and/or functions defined outside of such portion) that is within the limitations listed before. 

Let's look at an example:

	... (other code) ...
	start_nuxmv()
	
	b: bool = False
	x = 0
	
	while (x < 10 and not b):
		x += 1
	
	ltlspec("F x = 10")
	invarspec("!b")
	
	end_nuxmv()
	... (other code) ...
		
Let's notice some things:

+ The block of code that we want to isolate and test is enclosed within two functions, `start_nuxmv()` and `end_nuxmv()`. These functions do nothing, they are just placeholders. There can be as many of these functions as you like, but they should not be nested.

+ `b` is a boolean; this information needs to be specified in order to distinguish it from an `integer`, the default type assumed by `pynuxmv`.

+ At the end of the block you specify the conditions you want your program to comply with. These can be of two kinds, `LTL` formulas (`ltlspec`) or invariants (`invarspec`). More informations on LTL can be found on [wikipedia](https://en.wikipedia.org/wiki/Linear_temporal_logic). 

+ Finally: how do you test this portion of code? You simply run `pynuXmv` with the name of the source `.py` file to analyze and with the file name of the resulting `nuXmv` source code. You then launch `nuXmv` on these latter file, with an appropriate commands file (such as `unify`, which you can find in this repository).
	


