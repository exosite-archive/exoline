local temp_c = alias['temp_c'] 
local temp_f = alias['temp_f']
debug('Starting convert.lua...')
while true do
  local ts = temp_c.wait()
  local reading = temp_c[ts]
  local converted = reading * 1.8 + 32
  temp_f.value = converted
  debug(string.format('Converted %fC to %fF', reading, converted))
end
