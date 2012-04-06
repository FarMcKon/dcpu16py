#!/usr/bin/env python


import sys


class Cell:
	"""
	a cell enables us to pass around a reference to a register or memory location rather than the value
	"""
	def __init__(self, value=0):
		self.value = value


# offsets into DCPU16.registers
PC, SP, O = 8, 9, 10


OPCODES_ADVANCED  = {"JSR":0x1, "RROM":0x2,"AUD_O":0x3,"AUD_I":0x4}
OPCODES = {"SET": 0x1, "ADD": 0x2, "SUB": 0x3, "MUL": 0x4, "DIV": 0x5, "MOD": 0x6, "SHL": 0x7, "SHR": 0x8, "AND": 0x9, "BOR": 0xA, "XOR": 0xB, "IFE": 0xC, "IFN": 0xD, "IFG": 0xE, "IFB": 0xF}

audio_stream = []
class DCPU16:
	
	def __init__(self, memory):
		self.memory = [Cell(memory[i]) if i < len(memory) else Cell() for i in range(0x10000)]
		self.rom = [Cell(memory[i]) if i < len(memory) else Cell() for i in range(0x32)]
		self.rom[32] = 0x42	 #Vendor id for the series f knock-off chip
		self.registers = tuple(Cell() for _ in range(11))
		self.io =[Cell(),Cell()]
		self.skip = False
		self.tick = 0
		audio_stream.append((self.tick,0x00))
	def SET(self, a, b):
		a.value = b.value
		self.tick = self.tick +1 

	def ADD(self, a, b):
		o, r = divmod(a.value + b.value, 0x10000)
		self.registers[O].value = o
		a.value = r
		self.tick = self.tick +2 

	def SUB(self, a, b):
		o, r = divmod(a.value - b.value, 0x10000)
		self.registers[O].value = 0xFFFF if o == -1 else 0x0000
		a.value = r
		self.tick = self.tick +2 
	
	def MUL(self, a, b):
		o, r = divmod(a.value * b.value, 0x10000)
		a.value = r
		self.registers[O].value = o % 0x10000
		self.tick = self.tick +2 
	
	def DIV(self, a, b):
		if b.value == 0x0:
			r = 0x0
			o = 0x0
		else:
			r = a.value / b.value % 0x10000
			o = ((a.value << 16) / b.value) % 0x10000
		a.value = r
		self.registers[O].value = o
		self.tick = self.tick +3

	def MOD(self, a, b):
		if b.value == 0x0:
			r = 0x0
		else:
			r = a.value % b.value
		a.value = r
		self.tick = self.tick +3
	
	def SHL(self, a, b):
		r = a.value << b.value
		o = ((a.value << b.value) >> 16) % 0x10000
		a.value = r
		self.registers[O].value = o
		self.tick = self.tick +2 
	
	def SHR(self, a, b):
		r = a.value >> b.value
		o = ((a.value << 16) >> b.value) % 0x10000
		a.value = r
		self.registers[O].value = o
		self.tick = self.tick +2 
	
	def AND(self, a, b):
		a.value = a.value & b.value
		self.tick = self.tick +1 
  
	def BOR(self, a, b):
		a.value = a.value | b.value
		self.tick = self.tick +1 
	
	def XOR(self, a, b):
		a.value = a.value ^ b.value
		self.tick = self.tick +1 
	
	def IFE(self, a, b):
		self.skip = not (a.value == b.value)
		self.tick = self.tick +2 
		if self.skip == False:
			self.tick = self.tick +1 

	def IFN(self, a, b):
		self.skip = not (a.value != b.value)
		self.tick = self.tick +2 
		if self.skip == False:
			self.tick = self.tick +1 
	
	def IFG(self, a, b):
		self.skip = not (a.value > b.value)
		self.tick = self.tick +2 
		if self.skip == False:
			self.tick = self.tick +1 
   
	def IFB(self, a, b):
		self.skip = not ((a.value & b.value) != 0)
		self.tick = self.tick +2 
		if self.skip == False:
			self.tick = self.tick +1 
	
	def JSR(self, a, b):
		self.registers[SP].value = (self.registers[SP].value - 1) % 0x10000
		pc = self.registers[PC].value
		self.memory[self.registers[SP].value].value = pc
		self.registers[PC].value = b.value
		self.tick = self.tick +2 

	
	def RROM(self, a, b):
		print 'b value ' + str(b.value)
		a.value	 = self.rom[b.value].value
		self.tick = self.tick +2 
		print "rrom"
		exit(-20)

	def AUD_O(self, a, b):
		a.value = b.value #io[0] = register value 
		self.tick = self.tick +2 
		audio_stream.append((self.tick,a.value))
		print "aud_o at tick " + str(self.tick)

	def AUD_I(self, a, b):
		a.value = b.value
		self.tick = self.tick +2 
		print "aud_i at tick " + str(self.tick)
		exit(-20)
		
	def get_operand(self, a):
		if a < 0x08:
			arg1 = self.registers[a]
		elif a < 0x10:
			arg1 = self.memory[self.registers[a % 0x08].value]
		elif a < 0x18:
			next_word = self.memory[self.registers[PC].value].value
			self.registers[PC].value += 1
			#print "next word " + str(next_word)
			#print "reg_val: " + str(self.registers[a % 0x10].value)
			#print "reg: " + str(a % 0x10)
			arg1 = self.memory[next_word + self.registers[a % 0x10].value]
		elif a == 0x18:
			arg1 = self.memory[self.registers[SP].value]
			self.registers[SP].value = (self.registers[SP].value + 1) % 0x10000
		elif a == 0x19:
			arg1 = self.memory[self.registers[SP].value]
		elif a == 0x1A:
			self.registers[SP].value = (self.registers[SP].value - 1) % 0x10000
			arg1 = self.memory[self.registers[SP].value]
		elif a == 0x1B:
			arg1 = self.registers[SP]
		elif a == 0x1C:
			arg1 = self.registers[PC]
		elif a == 0x1D:
			arg1 = self.registers[O]
		elif a == 0x1E:
			arg1 = self.memory[self.memory[self.registers[PC].value].value]
			self.registers[PC].value += 1
		elif a == 0x1F:
			arg1 = self.memory[self.registers[PC].value]
			self.registers[PC].value += 1
		else:
			arg1 = Cell(a % 0x20)
		
		return arg1

	
	def run(self, debug=False):

		while True:
			pc = self.registers[PC].value
			w = self.memory[pc].value
			self.registers[PC].value += 1
			
			operands, opcode = divmod(w, 16)
			b, a = divmod(operands, 64)
			
			if debug:
				print "%04X: %04X" % (pc, w)
			
			if opcode == 0x00:
				if	a == OPCODES_ADVANCED["JSR"]:
					op = self.JSR
					arg1 = None
				elif  a == OPCODES_ADVANCED["RROM"]:
					op = self.RROM
					arg1 = self.registers[6]
					#arg2 loaded below 
					print "blarg2"
					exit(-2)
				elif  a == OPCODES_ADVANCED["AUD_O"]:
					op = self.AUD_O
					arg1 = self.io[0]
					#arg2 loaded below 
					#print "blarg3"
					#exit(-3)
				elif  a == OPCODES_ADVANCED["AUD_I"]:
					op = self.AUD_I
					arg1 = self.io[1] 
					print "blarg4"
					exit(-4)
				else:
					continue
			else:
				op = [
					None, self.SET, self.ADD, self.SUB,
					self.MUL, self.DIV, self.MOD, self.SHL,
					self.SHR, self.AND, self.BOR, self.XOR, self.IFE, self.IFN, self.IFG, self.IFB
				][opcode]
				arg1 = self.get_operand(a)
			
			arg2 = self.get_operand(b)
			
			if self.skip:
				if debug:
					print "skipping"
				self.skip = False
			else:
				op(arg1, arg2)
				if debug:
					self.dump_registers()
					self.dump_stack()
	
	def dump_registers(self):
		print " ".join("%s=%04X" % (["A", "B", "C", "X", "Y", "Z", "I", "J", "PC", "SP", "O"][i],
			self.registers[i].value) for i in range(11))
		print " ".join("%s=%04X" % (["AUDIO_OUT", "AUDIO_IN"][i],
			self.io[i].value) for i in range(len(self.io)) )
	
	def dump_stack(self):
		if self.registers[SP].value == 0x0:
			print "[]"
		else:
			print "[" + " ".join("%04X" % self.memory[m].value for m in range(self.registers[SP].value, 0x10000)) + "]"


if __name__ == "__main__":
	if len(sys.argv) == 2:
		program = []
		f = open(sys.argv[1])
		while True:
			hi = f.read(1)
			if not hi:
				break
			lo = f.read(1)
			program.append((ord(hi) << 8) + ord(lo))
		
		dcpu16 = DCPU16(program)
		dcpu16.run(debug=False)
		print audio_stream
	else:
		print "usage: ./dcpu16.py <object-file>"
