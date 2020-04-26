"""
<plugin key="TCW181BSNMP" name="Teracom TCW181B-CM (SNMP)" version="1.0.0" author="mboisnard">
    <params>
        <param field="Address" label="Server IP" width="200px" required="true"/>
        <param field="Port" label="Server Port" width="200px" required="true"/>
        <param field="Mode1" label="SNMP Public Community" width="200px" required="true" password="true"/>
        <param field="Mode2" label="SNMP Private Community" width="200px" required="true" password="true"/>
    </params>
</plugin>
"""
import Domoticz
from enum import IntEnum

import sys
if not '/usr/lib/python3.7/dist-packages' in sys.path:
  sys.path.append('/usr/lib/python3.7/dist-packages')


from pysnmp.hlapi import *


class SNMPCommand(IntEnum):
    ON = 1
    OFF = 0

class SNMPPlugin:

    oidPrefix = '1.3.6.1.4.1.38783'
    oidRelay1 = oidPrefix + '.3.2.0'
    oidRelay2 = oidPrefix + '.3.3.0'
    oidRelay3 = oidPrefix + '.3.4.0'
    oidRelay4 = oidPrefix + '.3.5.0'
    oidRelay5 = oidPrefix + '.3.6.0'
    oidRelay6 = oidPrefix + '.3.7.0'
    oidRelay7 = oidPrefix + '.3.8.0'
    oidRelay8 = oidPrefix + '.3.9.0'

    oidSaveConfiguration = oidPrefix + '.6.0'

    availableRelays = [oidRelay1, oidRelay2, oidRelay3, oidRelay4, oidRelay5, oidRelay6, oidRelay7, oidRelay8]
    relaysCount = len(availableRelays)
    
    deviceType = 17 # Lighting 2 - AC
    switchType = 0 # On/Off Switch

    # Plugin configuration
    snmpAddress = ''
    snmpPort = 161
    snmpPublicCommunity = ''
    snmpPrivateCommunity = ''

    def __init__(self):
        return

    def onStart(self):
        self.snmpAddress = Parameters["Address"]
        self.snmpPort = Parameters["Port"]
        self.snmpPublicCommunity = Parameters["Mode1"]
        self.snmpPrivateCommunity = Parameters["Mode2"]

        if (len(Devices) < self.relaysCount):
            Domoticz.Log('Create ' + str(self.relaysCount) + ' devices')

            # Range starts by 1 for name and unit (unit cannot be 0)
            for i in range(1, self.relaysCount + 1):
                Domoticz.Device(Name = 'Relay ' + str(i), Unit = i, Type = self.deviceType, Switchtype = self.switchType).Create()

    def onCommand(self, Unit, Command, Level, Hue):
        # Secure onCommand call to avoid array index outbound
        if Unit > self.relaysCount:
            return

        commandStr = str(Command)
        snmpCommand = SNMPCommand.ON if commandStr == 'On' else SNMPCommand.OFF

        resultCommand = self.writeSnmpCommand(self.availableRelays[Unit - 1], snmpCommand)
        resultSave = self.writeSnmpCommand(self.oidSaveConfiguration, SNMPCommand.ON)
            
        if (resultCommand == 0 and resultSave == 0):
            Devices[Unit].Update(nValue = int(snmpCommand), sValue = commandStr)

    def onHeartbeat(self):
        for unit in Devices:
            relayStatus = int(self.readSnmpCommand(self.availableRelays[unit - 1]))
            Devices[unit].Update(nValue = relayStatus, sValue = 'On' if relayStatus == 0 else 'Off')


    def readSnmpCommand(self, Oid):
        errorIndication, errorStatus, errorIndex, varBinds = next(
            getCmd(
                SnmpEngine(),
                CommunityData(self.snmpPublicCommunity),
                UdpTransportTarget((self.snmpAddress, self.snmpPort)),
                ContextData(),
                ObjectType(ObjectIdentity(Oid))
            )
        )

        if errorIndication:
            Domoticz.Error(str(errorIndication))
            return '0'
        elif errorStatus:
            Domoticz.Error('%s at %s' % (errorStatus.prettyPrint(), errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
            return '0'
        else:
            return varBinds[0][1].prettyPrint()

    def writeSnmpCommand(self, Oid, SnmpCommand):

        errorIndication, errorStatus, errorIndex, varBinds = next(
            setCmd(
                SnmpEngine(),
                CommunityData(self.snmpPrivateCommunity, mpModel = 0),
                UdpTransportTarget((self.snmpAddress, self.snmpPort)),
                ContextData(),
                ObjectType(ObjectIdentity(Oid), Integer(int(SnmpCommand)))
            )
        )

        if errorIndication:
            Domoticz.Error(str(errorIndication))
            return -1
        elif errorStatus:
            Domoticz.Error('%s at %s' % (errorStatus.prettyPrint(), errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
            return -1

        return 0

global _plugin
_plugin = SNMPPlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()