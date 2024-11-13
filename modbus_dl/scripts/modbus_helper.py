import os, sys, socket, datetime, time, math, csv, json, signal, toml
from umodbus.client import tcp
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from data_helper import DataHelper

class ModbusHelper(object):

	FUNCTION_CODES = {
		'01': ['1','01','FC01','coil','Coil','coils','Coils','RC','Coil-FC01'],			# function code 01: Read Coils
		'02': ['2','02','FC02','discrete','Discrete','di','DI','RDI','DI-FC02'], 		# function code 02: Read Discrete Inputs
		'03': ['3','03','FC03','holding','Holding','HR','RHR','HR-FC03'], 				# function code 03: Read Holding Registers
		'04': ['4','04','FC04','input register','input registers','Input Register',
				'Input Registers','IR','RIR','IR-FC04']									# function code 04: Read Input Registers
	}

	UMODBUS_TCP_CALL = {
		'01': tcp.read_coils,
		'02': tcp.read_discrete_inputs,
		'03': tcp.read_holding_registers,
		'04': tcp.read_input_registers
	}

	DATA_TYPES_REGISTER_COUNT = {
		'uint16': 1,
		'sint16': 1,
		'float32': 2,
		'float64': 4,
		'packedbool': 1,
		'ruint16': 1,
		'rsint16': 1,
		'rfloat32_byte_swap': 2, # [A B C D] -> [B A] [D C]
		'rfloat32_word_swap': 2, # [A B C D] -> [C D] [A B]
		'rfloat32_byte_word_swap': 2, # [A B C D] -> [D C] [B A]
		#'rfloat64': 4, # unsupported at the moment, to be added; "reverse" float64 for Little-Endian interpretation
		'di': 1,
		'coil': 1
	}

	@classmethod
	def transform_data(cls, input_dict):
		result = []
		for key, value in input_dict.items():
			transformed_item = {
				'address': value[0],
				'read_type': value[1],
				'data_type': value[2],
				'tag_name': value[3],
				'scaling_coeff': value[4],
				'scaling_offset': value[5]
			}
			result.append(transformed_item)
		return result
	
	# Method to parse a Modbus template .csv configuration file and build the various Modbus TCP calls the client shall send in an "optimized" way (optimized to reduce/minimize the number of calls)
	# it returns 2 elements: call_groups and interpreter_helper
	@classmethod
	def parse_template_build_calls(cls, modbus_config):
		call_groups = {}
		interpreter_helper = {}
		template_lod = cls.transform_data(modbus_config)
		
		# find unique/distinct read_type
		for read_entry in template_lod:
			read_address = read_entry['address']

			# skip entry if there is no address (mandatory field)
			if (not read_address) or (read_address == '') or (read_address is None):
				print('\n\t[WARNING] On item:',read_entry)
				print('\t[WARNING] Skipping item due to no address provided')
				continue

			read_type = str(read_entry['read_type'])
			read_tag_name = read_entry['tag_name']

			# skip entry if there is no read_type (mandatory field)
			if (not read_type) or (read_type == '') or (read_type is None):
				print('\n\t[WARNING] On item:',read_entry)
				print('\t[WARNING] Skipping item with address '+str(read_address)+' and tag_name "'+str(read_tag_name)+'"" due to no read_type provided\n')
				continue			
			
			# default to data_type of sint16 if user forgot to specify one
			# arbitrary choice to accomodate errors in the modbus_template...
			# logged data may be inaccurate if the real data_type is different from sint16
			read_data_type = read_entry['data_type']
			if (not read_data_type) or (read_data_type == '') or (read_data_type is None):
				print('\n\t[WARNING] No data_type specified in modbus_template for item:')
				print('\t\t',read_entry)
				print('\tAssuming default data_type of "sint16"')
				print('\t[WARNING] Logged data may be inaccurate for this item!')
				read_data_type = 'sint16'
			# skip entry if read_data_type is unknown or not currently supported
			if read_data_type not in ModbusHelper.DATA_TYPES_REGISTER_COUNT:
				print('\n\t[WARNING] On item:',read_entry)
				print('\t[WARNING] Skipping item with address '+str(read_address)+' and tag_name "'+str(read_tag_name)+'"" due to unknown or unsupported read_type of "'+str(read_data_type)+'"')
				print('\t[WARNING] Supported read_types are:',[str(i) for i in ModbusHelper.DATA_TYPES_REGISTER_COUNT])
				continue

			# create a default tag name if the user forgot to specify one
			if (not read_tag_name) or (read_tag_name == '') or (read_tag_name is None):
				print('\n\t[WARNING] No tag_name specified in modbus_template for item:')
				print('\t\t',read_entry)
				print('\tUsing default tag_name of: "'+read_type+'_address_'+str(read_address)+'_data_type_'+read_data_type+'"')

			# do I really need to look at scaling here if my goal is only to parse the configuration template and build the Modbus TCP calls???
			#address_read_scaling_coeff = read_entry['scaling_coeff']
			#address_read_scaling_offset = read_entry['scaling_offset']

			# lookup the read_type in ModbusHelper.FUNCTIONS_CODES and build the lookup table
			fc_lookup_table = {}			

			fc_found = False
			for fc in ModbusHelper.FUNCTION_CODES:
				if fc_found:
					break
				for fc_keyword in ModbusHelper.FUNCTION_CODES[fc]:
					if fc_keyword in read_type:
						fc_found = True
						if read_type not in fc_lookup_table:
							fc_lookup_table[read_type] = fc
						if fc not in call_groups:
							call_groups[fc] = []
							#interpreter_helper[fc] = {'addresses': [],'address_count_map': {},'address_data_type_map':{},'address_tag_name_map': {}}
							interpreter_helper[fc] = {'addresses': [],'address_maps': {}}

						#interpreter_helper[fc]['address_count_map'][int(read_address)] = ModbusHelper.DATA_TYPES_REGISTER_COUNT[read_data_type]
						#interpreter_helper[fc]['address_data_type_map'][int(read_address)] = read_data_type
						#interpreter_helper[fc]['address_tag_name_map'][int(read_address)] = read_tag_name
						interpreter_helper[fc]['address_maps'][int(read_address)] = {}
						interpreter_helper[fc]['address_maps'][int(read_address)]['count'] = ModbusHelper.DATA_TYPES_REGISTER_COUNT[read_data_type]
						interpreter_helper[fc]['address_maps'][int(read_address)]['data_type'] = read_data_type
						interpreter_helper[fc]['address_maps'][int(read_address)]['tag_name'] = read_tag_name
						interpreter_helper[fc]['address_maps'][int(read_address)]['scaling_coeff'] = read_entry['scaling_coeff']
						interpreter_helper[fc]['address_maps'][int(read_address)]['scaling_offset'] = read_entry['scaling_offset']

						for call_address in range(int(read_address),int(read_address)+ModbusHelper.DATA_TYPES_REGISTER_COUNT[read_data_type]):
							interpreter_helper[fc]['addresses'].append(call_address)
						break
		
		for fc in interpreter_helper:
			previous_address = None
			for address in sorted(interpreter_helper[fc]['addresses']):
				if previous_address is None:
					call_groups[fc].append({'start_address': address, 'register_count': 1})
				else:
					address_delta = address - previous_address
					if address_delta == 1:
						call_groups[fc][-1]['register_count'] += 1						
					else:
						call_groups[fc].append({'start_address': address, 'register_count': 1})
				previous_address = address

		return call_groups, interpreter_helper
	
	@classmethod
	def chech_port_id_records(cls, config: dict = None, key = None, key_value = None, full_path_to_modbus_config_toml = None):
		if not isinstance(key_value,int):
			print('\t[ERROR] Error parsing config file:',str(full_path_to_modbus_config_toml))
			print('\t[ERROR] value of key "'+str(key)+'" should be of type "integer" (int)')
			print('\t[ERROR] current type of value for key "'+str(key)+'" is',type(key_value),'and current value is config["'+str(key)+'"] =',str(key_value))
			return 0
		# check for valid TCP port range
		if key == 'server_port':
			if not (key_value in range(1,65536)):
				print('\t[ERROR] Error parsing config file:',str(full_path_to_modbus_config_toml))
				print('\t[ERROR] invalid TCP port "'+str(key_value)+'" out of valid range [1,65535] for TCP ports')
				return 0
			elif key_value not in [502,503]:
				print('\t[WARNING] "server_port" from config file not in common Modbus TCP port list [502,503]:',str(key_value),'\n')
				return 2
		# check for valid Modbus Server ID
		elif key == 'server_id':
			if not (key_value in range(0,256)):
				print('\t[ERROR] Error parsing config file:',str(full_path_to_modbus_config_toml))
				print('\t[ERROR] invalid server ID "'+str(key_value)+'" out of valid range [0,255]')
				return 0
		# ensure only strictly positive values configured
		elif key == 'in_memory_records':
			if not key_value > 0:
				print('\t[ERROR] Error parsing config file:',str(full_path_to_modbus_config_toml))
				print('\t[ERROR] for key "'+str(key)+'", please provide a strictly positive value > 0 (0 NOT allowed!)')
				print('\t[ERROR] current value provided is',str(key_value))
				return 0
		
		return 1
	
	@classmethod
	def check_ip_type_name(cls, config: dict = None, key = None, key_value = None, full_path_to_modbus_config_toml = None):
		
		if not isinstance(key_value,str):
			print('\t[ERROR] Error parsing config file:',str(full_path_to_modbus_config_toml))
			print('\t[ERROR] value of key "'+str(key)+'" should be of type "string" (str)')
			print('\t[ERROR] current type of value for key "'+str(key)+'" is',type(key_value),'and current value is config["'+str(key)+'"] =',str(key_value))
			return 0
		# check for valid IP address format and content
		if key == 'server_ip':					
			if key_value in ['localhost','Localhost','LocalHost','LOCALHOST','Local Host','LOCAL HOST','local host']:
				config[key] = 'localhost'
				return 2
			else:
				key_value_split = key_value.split('.')
				if not (len(key_value_split) == 4):
					print('\t[ERROR] Error parsing config file:',str(full_path_to_modbus_config_toml))
					print('\t[ERROR] incorrect IPv4 address format provided:',str(key_value))
					print('\t[ERROR] please provide a valid IPv4 address format A.B.C.D with A, B, C, and D in range [0,255]')
					return 0
				else:
					for octet in key_value_split:
						if not octet.isnumeric():
							print(octet,type(octet))
							print('\t[ERROR] Error parsing config file:',str(full_path_to_modbus_config_toml))
							print('\t[ERROR] incorrect IPv4 address format provided:',str(key_value))
							print('\t[ERROR] octet "'+str(octet)+'" is not convertible to type int')
							print('\t[ERROR] please provide a valid IPv4 address format A.B.C.D with A, B, C, and D in range [0,255]')
							return 0
						elif (int(octet) < 0) or (int(octet) > 255):
							print('\t[ERROR] Error parsing config file:',str(full_path_to_modbus_config_toml))
							print('\t[ERROR] incorrect IPv4 address provided:',str(key_value))
							print('\t[ERROR] octet "'+str(octet)+'" shall be in range [0,255]')
							print('\t[ERROR] please provide a valid IPv4 address format A.B.C.D with A, B, C, and D in range [0,255]')
							return 0
						
		elif key == 'log_file_type':
			if key_value not in ['csv','json']:
				print('\t[ERROR] Error parsing config file:',str(full_path_to_modbus_config_toml))
				print('\t[ERROR] invalid/not supported "log_file_type" provided:',str(key_value))
				print('\t[ERROR] please provide a valid/supported log_file_type, either "csv" or "json"')
				return 0 
			
		# remove ambiguous characters for log_file_name, replace them with "_"
		elif key == 'log_file_name':
			for ambiguous_char in ['`','~','!','@','#','$','%','^','&','*','(',')','+','=',',','.','?','/','<','>','{','}','[',']','|']:
				if ambiguous_char in key_value:
					print('\t[WARNING] Ambiguous character(s) "'+str(ambiguous_char)+'" found in "log_file_name":',str(key_value))
					print('\t[WARNING] will be replace by "_":',str(key_value.replace(ambiguous_char,'_')))
					config[key] = key_value.replace(ambiguous_char,'_')
					key_value = config[key]

		return 1
		

	@classmethod
	def parse_json_config(cls, full_path_to_modbus_config_toml):

		# with open(full_path_to_modbus_config_toml) as json_file:
		# 	config = json.load(json_file)
		# json_file.close()
		config = toml.load(full_path_to_modbus_config_toml)['modbus_dl']
		config_compound = toml.load(full_path_to_modbus_config_toml).get('compound', {})
		
		# perform input validation
		for key in config:
			key_value = config[key]

			if key == 'town':
				for town in config[key]:
					for ip in config[key][town]:
					
						tmp = cls.check_ip_type_name(config[key], 'server_ip', ip.replace('_','.'), full_path_to_modbus_config_toml)
						if tmp == 0: return
						elif tmp == 2:continue

						for id in config[key][town][ip]:
							
							tmp = cls.chech_port_id_records(config, 'server_id', int(id), full_path_to_modbus_config_toml)
							if tmp == 0: return
							elif tmp == 2: continue

			# for keys/values that should be entered as string
			elif key in ['log_file_type','log_file_name']:
				tmp = cls.check_ip_type_name(config, key, key_value, full_path_to_modbus_config_toml)
				if tmp == 0: return
				elif tmp == 2:continue

			# for keys/values that should be entered as integer
			elif key in ['server_port','in_memory_records']:
				tmp = cls.chech_port_id_records(config, key, key_value, full_path_to_modbus_config_toml)
				if tmp == 0: return
				elif tmp == 2:continue

			# for keys/values that should be entered as either integer or null
			elif key in ['json_indent']:
				if (not isinstance(key_value,int)) and (not key_value is None):
					print('\t[ERROR] Error parsing config file:',str(full_path_to_modbus_config_toml))
					print('\t[ERROR] value of key "'+str(key)+'" should be of type "integer" (int) or "NoneType" (null)')
					print('\t[ERROR] current type of value for key "'+str(key)+'" is',type(key_value),'and current value is config["'+str(key)+'"] =',str(key_value))
					return				
				if key == 'json_indent':
					if key_value is None:
						continue
					# if not None, ensure only positive or zero integer values configured
					elif not key_value >= 0:
						print('\t[ERROR] Error parsing config file:',str(full_path_to_modbus_config_toml))
						print('\t[ERROR] for key "'+str(key)+'", please provide a positive value >= 0 (0 allowed)')
						print('\t[ERROR] current value provided is',str(key_value))
						return

			# for keys/values that should be entered as either integer or float
			elif key in ['poll_interval_seconds','server_timeout_seconds']:
				if not (isinstance(key_value,int) or isinstance(config[key],float)):
					print('\t[ERROR] Error parsing config file:',str(full_path_to_modbus_config_toml))
					print('\t[ERROR] value of key "'+str(key)+'" should be of type "integer" (int) or "float" (float)')
					print('\t[ERROR] current type of value for key "'+str(key)+'" is',type(key_value),'and current value is config["'+str(key)+'"] =',str(key_value))
					return

			# for keys/values that should be entered as dictionary
			elif key in ['file_rotation']:
				if not isinstance(key_value,dict):
					print('\t[ERROR] Error parsing config file:',str(full_path_to_modbus_config_toml))
					print('\t[ERROR] value of key "'+str(key)+'" should be of type "dictionary" (dict)')
					print('\t[ERROR] current type of value for key "'+str(key)+'" is',type(key_value),'and current value is config["'+str(key)+'"] =',str(key_value))
					return
				# for keys/values that should be entered as integer
				for sub_key in key_value:
					sub_key_value = config[key][sub_key]
					if sub_key in ['max_file_records']:
						if not isinstance(sub_key_value,int):
							print('\t[ERROR] Error parsing config file:',str(full_path_to_modbus_config_toml))
							print('\t[ERROR] value of sub_key "'+str(sub_key)+'" should be of type "integer" (int)')
							print('\t[ERROR] current type of value for sub_key "'+str(sub_key)+'" is',type(sub_key_value),'and current value is config["'+str(key)+'"]["'+str(sub_key)+'"] =',str(sub_key_value))
							return
					if sub_key == 'max_file_records':
						if not (sub_key_value > 0):
							print('\t[ERROR] Error parsing config file:',str(full_path_to_modbus_config_toml))
							print('\t[ERROR] value of sub_key "'+str(sub_key)+'" should be an integer >= 1')
							print('\t[ERROR] current value for sub_key "'+str(sub_key)+'" is',str(sub_key_value))
							return
		return config, config_compound

class ModbusTCPClient:
	def __init__(self, server_ip=None, server_port=None, server_id=None, poll_interval_seconds=None):
		if server_ip is None:
			print('\t[ERROR] no server_ip argument provided to ModbusTCPClient instance')
			print('\t[ERROR] server_port, server_id and poll_interval_seconds arguments will default to 502, 1, and 1 second respectively if not specified')
			print('\t[ERROR] at a minimum, the ModbusTCPClient should know which IP address to connect to')
			print('\t[ERROR] here are some examples:')
			print('\t[ERROR]\t\tmy_tcp_client = ModbusTCPClient("10.1.10.30")\t# connect to Modbus TCP Server @ 10.1.10.30 on default port 502 and with default ID 1')
			print('\t[ERROR]\t\tmy_tcp_client = ModbusTCPClient(server_ip="10.1.10.31", server_port=503, server_id=10, poll_interval_seconds=5)\t# connect to Modbus TCP Server @ 10.1.10.31 on port 503, with ID 10 and poll every 5 seconds')
			return
		else:
			self.modbus_tcp_server_ip_address = server_ip
		default_server_port = ''
		if server_port is None:
			default_server_port = '(default)'
			server_port = 502
		self.modbus_tcp_server_port = server_port
		default_server_id = ''
		if server_id is None:
			default_server_id = '(default)'
			server_id = 1
		self.modbus_tcp_server_id = server_id
		default_poll_interval = ''
		if poll_interval_seconds is None:
			default_poll_interval = '(default)'
			poll_interval_seconds = 1
		self.poll_interval_seconds = poll_interval_seconds
		self.call_groups = None
		self.interpreter_helper = None
		self.sock = None
		print('\t[INFO] Client will attempt to connect to Modbus TCP Server at:\t\t\t',str(self.modbus_tcp_server_ip_address))
		print('\t[INFO] Client will attempt to connect to Modbus TCP Server on port:\t\t',str(self.modbus_tcp_server_port),default_server_port)
		print('\t[INFO] Client will attempt to connect to Modbus TCP Server with Modbus ID:\t',str(self.modbus_tcp_server_id),default_server_id)
		print('\t[INFO] Client will attempt to poll the Modbus TCP Server every:\t\t\t',str(self.poll_interval_seconds)+' seconds',default_poll_interval)

	def load_template(self, modbus_config=None):
		# if full_path_to_modbus_template_csv is None:
		# 	print('\t[ERROR] in ModbusTCPClient.load_template(): please make sure to provide a valid path to a modbus_template.csv file')
		# 	return
		# elif not os.path.isfile(full_path_to_modbus_template_csv):
		# 	print('\t[ERROR] in ModbusTCPClient.load_template(): unable to find "'+str(full_path_to_modbus_template_csv)+'"')
		# 	return
		# else:
		self.call_groups, self.interpreter_helper = ModbusHelper.parse_template_build_calls(modbus_config)

	def connect(self, timeout=5):
		socket.setdefaulttimeout(timeout)
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)		
		self.sock.connect((self.modbus_tcp_server_ip_address, self.modbus_tcp_server_port))

	def set_sensor_id(self, sernsor_id: int = 1):
		self.modbus_tcp_server_id = sernsor_id

	def disconnect(self):
		self.sock.close()

	def reconnect(self):
		self.disconnect()
		self.connect()

	def interpret_response(self, response, fc, start_address):
		interpreted_response = {}
		skip_next = False
		skip_count = 0
		for i in range(len(response)):
			address_index = i + start_address
			if fc in ['01', '02']:
				#interpreted_response[self.interpreter_helper[fc]['address_tag_name_map'][address_index]] = response[i]
				interpreted_response[self.interpreter_helper[fc]['address_maps'][address_index]['tag_name']] = response[i]
			else:
				if skip_next:
					if skip_count == 0:
						skip_next = False
					elif skip_count == 1:
						skip_count -= 1
						skip_next = False
					else:
						skip_count -= 1
					continue								

				#given_data_type = self.interpreter_helper[fc]['address_data_type_map'][address_index]
				given_data_type = self.interpreter_helper[fc]['address_maps'][address_index]['data_type']
				if given_data_type == 'float32':
					float_32_items = response[i:i+2]
					float_32_binaries = [DataHelper.int_16_unsigned_to_binary(reg) for reg in float_32_items]
					rv = DataHelper.binary_32_to_ieee_754_single_precision_float(''.join(float_32_binaries))
					skip_next = True
				elif given_data_type == 'sint16':
					rv = DataHelper.int_16_unsigned_to_signed(response[i])
					skip_next = False
				elif given_data_type == 'uint16':
					rv = response[i]
					skip_next = False
				elif given_data_type == 'float64':
					float_64_items = response[i:i+4]
					float_64_binaries = [DataHelper.int_16_unsigned_to_binary(reg) for reg in float_64_items]
					rv = DataHelper.binary_64_to_ieee_754_single_precision_float(''.join(float_64_binaries))
					skip_next = True
					skip_count = 3
				elif given_data_type == 'rsint16':
					swapped_rv = DataHelper.binary_string_16_bits_to_int_16_unsigned(DataHelper.int_16_swap_bytes(DataHelper.int_16_unsigned_to_binary(response[i])))
					rv = DataHelper.int_16_unsigned_to_signed(swapped_rv)
					skip_next = False
				elif given_data_type == 'ruint16':
					rv = DataHelper.binary_string_16_bits_to_int_16_unsigned(DataHelper.int_16_swap_bytes(DataHelper.int_16_unsigned_to_binary(response[i])))					
					skip_next = False
				elif given_data_type == 'packedbool':
					binary_string_register = DataHelper.int_16_unsigned_to_binary(response[i])
					binary_string_register_list = []
					binary_string_register_list[:0]= binary_string_register 
					skip_next = False
				elif given_data_type == 'rfloat32_byte_swap':
					float_32_items = response[i:i+2]
					float_32_binary_string = ''.join([DataHelper.int_16_unsigned_to_binary(reg) for reg in float_32_items])
					swapped_rv = DataHelper.float32_swap_bytes(float_32_binary_string)
					rv = DataHelper.binary_32_to_ieee_754_single_precision_float(swapped_rv)
					skip_next = True
				elif given_data_type == 'rfloat32_word_swap':
					float_32_items = response[i:i+2]
					float_32_binary_string = ''.join([DataHelper.int_16_unsigned_to_binary(reg) for reg in float_32_items])
					swapped_rv = DataHelper.float32_swap_words(float_32_binary_string)
					rv = DataHelper.binary_32_to_ieee_754_single_precision_float(swapped_rv)
					skip_next = True
				elif given_data_type == 'rfloat32_byte_word_swap':
					float_32_items = response[i:i+2]
					float_32_binary_string = ''.join([DataHelper.int_16_unsigned_to_binary(reg) for reg in float_32_items])
					swapped_rv = DataHelper.float32_swap_bytes_words(float_32_binary_string)
					rv = DataHelper.binary_32_to_ieee_754_single_precision_float(swapped_rv)
					skip_next = True
				else:
					print('\t[ERROR] unsupported data_type of "'+str(given_data_type)+'" on tag_name = "'+self.interpreter_helper[fc]['address_maps'][address_index]['tag_name']+'"')
					skip_next = False
					continue

				# evaluate scaling to apply
				applied_coeff = self.interpreter_helper[fc]['address_maps'][address_index]['scaling_coeff']
				applied_offset = self.interpreter_helper[fc]['address_maps'][address_index]['scaling_offset']
				if (not applied_coeff) ^ (not applied_offset):
					one_scaling_null = True
					applied_coeff_null = not applied_coeff
					both_null_case = False
				elif (not applied_coeff) & (not applied_offset):
					both_null_case = True
				else:
					applied_coeff_null = (math.isnan(float(applied_coeff)) or (applied_coeff is None))
					one_scaling_null =  applied_coeff_null ^ (math.isnan(float(applied_offset)) or (applied_offset is None))
					both_null_case = (math.isnan(float(applied_coeff)) or (applied_coeff is None)) & (math.isnan(float(applied_offset)) or (applied_offset is None))
				if not both_null_case:
					if not (given_data_type == 'packedbool'):
						if one_scaling_null:
							if applied_coeff_null:
								applied_coeff = 1
							else:
								applied_offset = 0
						rv = rv*float(applied_coeff) + float(applied_offset)

				if given_data_type == 'packedbool':					
					interpreted_response[self.interpreter_helper[fc]['address_maps'][address_index]['tag_name']+'_uint16_value'] = response[i]
					for string_char_pos, string_char in enumerate(binary_string_register_list):
						suffix = str(15 - string_char_pos)
						interpreted_response[self.interpreter_helper[fc]['address_maps'][address_index]['tag_name']+'_bit'+suffix] = int(string_char)
				else:
					interpreted_response[self.interpreter_helper[fc]['address_maps'][address_index]['tag_name']] = rv

		return interpreted_response
	
	def combine_tag_responses(self, lod):
		combined_responses = {}
		for resp in lod:
			for tag in resp:
				combined_responses[tag] = resp[tag]
		return combined_responses

	def cycle_poll(self, time_format = '%Y-%m-%d %H:%M:%S%z'):
		ts_local = datetime.datetime.now().astimezone()
		ts_utc = ts_local.astimezone(datetime.timezone.utc)
		all_interpreted_responses = [{'timestamp_utc': ts_utc.strftime(time_format), 'timestamp_local': ts_local.strftime(time_format)}]
		for modbus_call in self.call_groups:
			modbus_request = ModbusHelper.UMODBUS_TCP_CALL[modbus_call]
			for query in self.call_groups[modbus_call]:
				message = modbus_request(slave_id=self.modbus_tcp_server_id, starting_address=query["start_address"], quantity=query["register_count"])

				# Response depends on Modbus function code.
				try:
					response = tcp.send_message(message, self.sock)
					# print(response[106], response[107])
					interpreted_response = self.interpret_response(response, modbus_call, query['start_address'])
					all_interpreted_responses.append(interpreted_response)
				except Exception as err:
					print(f"Didn't get a result from the registry {self.modbus_tcp_server_ip_address} {self.modbus_tcp_server_id} {query['start_address']}")
					print(f'Error: answer with server {err}')

		combined_responses = self.combine_tag_responses(all_interpreted_responses)
		return combined_responses

	def pretty_print_interpreted_response(self, to_print, max_items_per_line=2):
		headers = list(to_print.keys())		
		header_max_length = max([len(str(h)) for h in headers])
		values = list(to_print.values())
		value_max_length = max([len(str(v)) for v in values])
		max_length = max(header_max_length,value_max_length)

		headers_padded = [h.ljust(max_length) for h in headers]
		values_padded = [str(v).ljust(max_length) for v in values]
		
		print('')
		for i in range(0,len(headers_padded),max_items_per_line):			
			header_line = ' | '.join(str(x) for x in headers_padded[i:i+max_items_per_line])
			value_line = ' | '.join(str(v) for v in values_padded[i:i+max_items_per_line])
			sep_line = '-'.ljust(len(header_line),'-')
			print('\t',sep_line)
			print('\t',header_line)
			print('\t',value_line)
		print('\t',sep_line)
		print('')

class ModbusTCPDataLogger:
	def termination_signal_handler(self):
		print(f'\nSave data {self.modbus_tcp_client.modbus_tcp_server_ip_address}!')
		if self.data_logging:
			self.write_data_to_disk(self.data_log['data'], self.modbus_config['log_file_type'], self.modbus_config['log_file_name'])
			# self.rotate_file(self.modbus_config['log_file_type'], self.modbus_config['log_file_name'])
		self.modbus_tcp_client.disconnect()


	def write_data_to_disk(self, data, log_file_type, log_file_name):
		tmp_date = {
			"data_logs": []
		}

		full_path_to_log_file = os.path.join(
			self.log_file_location,log_file_name + '_'
			+ self.modbus_tcp_client.modbus_tcp_server_ip_address
			+ '.' + log_file_type)
		if not os.path.exists(full_path_to_log_file):
			if log_file_type == 'csv':
				DataHelper.lod_to_csv(
						lod = data, 
						full_path_to_csv_file = full_path_to_log_file
					)
			elif log_file_type == 'json':
				tmp_date['data_logs'].append(data)
				with open(full_path_to_log_file, 'w') as fp:
					json.dump(tmp_date, fp, indent=self.modbus_config['json_indent'])
				fp.close()
		else:
			if log_file_type == 'csv':
				with open(full_path_to_log_file, 'a', newline='') as csv_log:
					for record in data:
						csv_log_append = csv.writer(csv_log)
						csv_log_append.writerow(list(record.values()))
			elif log_file_type == 'json':
				with open(full_path_to_log_file,'r+') as json_log:
					json_data = json.load(json_log)
					json_data['data_logs'].append(data)
					json_log.seek(0)
					json.dump(json_data, json_log, indent=self.modbus_config['json_indent'])
		return

	def rotate_file(self, log_file_type, log_file_name):
		full_path_to_log_file = os.path.join(self.log_file_location,log_file_name+'.'+log_file_type)
		# ts_str = str(int(time.time())) #str(time.time_ns())
		full_path_to_log_file_rotated = os.path.join(self.log_file_location,log_file_name+'_'+ self.modbus_tcp_client.modbus_tcp_server_ip_address+'.'+log_file_type)
		os.rename(full_path_to_log_file, full_path_to_log_file_rotated)

	def create_data_for_db(self, data = None, data_log = None, town = None, ):
		if town not in data:
			data[town] = {'timestamp_utc': data_log.pop('timestamp_utc')}

		del data_log['timestamp_local']

		for id_register in data_log:
			id = id_register.split("_")[2]
			register = id_register.split("_")[-1]
			compound = self.compound_name.get(town, {}).get(id, {}).get(register)
			value = data_log[id_register]

			# formatted_value = f'{value / 1000}' if compound is None else f'{value / 1000} {compound}'
			formatted_value = value / 1000
			
			if 'compound' not in data[town]:
				data[town]['compound'] = {}

			if compound not in data[town]['compound']:
				data[town]['compound'][compound] = formatted_value
		

		return data

		

	def __init__(self, full_path_to_modbus_config_toml=None, full_path_to_logged_data=None, quiet=False, data_logging=True):
		if full_path_to_modbus_config_toml is None:
			print('\t[ERROR] a Modbus config.json file is required for a ModbusTCPDataLogger instance')
			print('\t[ERROR] please provide the full path to the Modbus config.json file')
			return
		# if full_path_to_modbus_template_csv is None:
		# 	print('\t[ERROR] a Modbus template.csv file is required for a ModbusTCPDataLogger instance')
		# 	print('\t[ERROR] please provide the full path to the Modbus template.csv file')
		# 	return
		if full_path_to_logged_data is None:
			print('\t[WARNING] no explicit path location provided on where to store data log files on the local system')
			default_path_to_data_files = os.path.dirname(os.path.realpath(__file__)).replace('scripts', 'data')
			print('\t[WARNING] will default to using:', str(default_path_to_data_files))
			if not os.path.isdir(default_path_to_data_files):
				os.mkdir(default_path_to_data_files)
			full_path_to_logged_data = default_path_to_data_files
		if not data_logging:
			print('\t[WARNING] data logging functionality has been explicitely disbaled by setting data_logging=False')
			print('\t[WARNING] this overwrites the "quiet" argument and means that quiet=False')
			quiet = False
		self.data_logging = data_logging
		self.log_file_location = full_path_to_logged_data
		self.data_for_db = {}
				
		self.data_log = {
			'in_memory_records': 0,
			'written_to_live_file_records': 0
		}
		self.modbus_config, self.compound_name = ModbusHelper.parse_json_config(full_path_to_modbus_config_toml)
		if self.modbus_config is None:
			print('\t[ERROR] An error occured while parsing the Modbus json configuration file!')
			print('\t[ERROR] Please review the error messages, correct the Modbus json configuration file and try again.')
			print('\t[ERROR] Now exiting Python with sys.exit()')
			sys.exit()

		for town_name in self.modbus_config['town']:
			for ip_address in self.modbus_config['town'][town_name]:
				if self.modbus_config['log_file_type'] == 'csv':
					self.data_log['data'] = []
				elif self.modbus_config['log_file_type'] == 'json':
					self.data_log['data'] = {}
				else:
					print('\t[ERROR] on "log_file_type": '+str(self.modbus_config['log_file_type']))
					print('\t[ERROR] currently supported log_file_type are either "csv" or "json"')
					print('\t[ERROR] Now exiting Python with sys.exit()')
					sys.exit()

				connect = False

				self.modbus_tcp_client = ModbusTCPClient(
							server_ip=ip_address.replace('_','.'),
							server_port=self.modbus_config['server_port'],
							poll_interval_seconds=self.modbus_config['poll_interval_seconds']
						)
				try:
					
					for sensor_id in self.modbus_config['town'][town_name][ip_address]:	
						if self.modbus_config['town'][town_name][ip_address][sensor_id].get('port'):
							self.modbus_tcp_client.modbus_tcp_server_port = self.modbus_config['town'][town_name][ip_address][sensor_id].pop("port")
							self.modbus_tcp_client.connect(self.modbus_config['server_timeout_seconds'])

						elif not connect:
							self.modbus_tcp_client.connect(self.modbus_config['server_timeout_seconds'])
							connect = True

						self.modbus_tcp_client.set_sensor_id(int(sensor_id))
						self.modbus_tcp_client.load_template(self.modbus_config['town'][town_name][ip_address][sensor_id])

						# print('Press Ctrl+C to stop and exit gracefully...')
						modbus_poll_response = self.modbus_tcp_client.cycle_poll()			
						
						if self.data_logging:
							# continue to load records in memory as long as in_memory_records threshold is not met
							self.data_log['data'].update(modbus_poll_response)

						if not quiet:
							self.modbus_tcp_client.pretty_print_interpreted_response(modbus_poll_response)
							print('Press Ctrl+C to stop and exit gracefully...')
						# time.sleep(self.modbus_config['poll_interval_seconds'])
				except Exception as err:
					print(f"Error: {err}")
					if town_name not in self.data_for_db:
						self.data_for_db[town_name] = None
					continue
				self.termination_signal_handler()
				self.create_data_for_db(self.data_for_db, self.data_log['data'], town_name)
		