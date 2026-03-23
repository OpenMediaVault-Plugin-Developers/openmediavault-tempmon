<?php
/**
 * Copyright (C) 2022-2026 openmediavault plugin developers
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
class OMVRpcServiceTempMon extends \OMV\Rpc\ServiceAbstract
{
    public function getName()
    {
        return "TempMon";
    }

    public function initialize()
    {
        $this->registerMethod("getSensorsList");
        $this->registerMethod("getSensor");
        $this->registerMethod("setSensor");
        $this->registerMethod("deleteSensor");
        $this->registerMethod("getAll");
    }

    public function getSensorsList($params, $context)
    {
        // Validate the RPC caller context.
        $this->validateMethodContext($context, ["role" => OMV_ROLE_ADMINISTRATOR]);
        // Validate the parameters of the RPC service method.
        $this->validateMethodParams($params, "rpc.common.getlist");
        // Get the configuration object.
        $db = \OMV\Config\Database::getInstance();
        $objects = $db->getAssoc("conf.service.tempmon.sensor");
        foreach ($objects as &$obj) {
            $obj['currenttemp'] = $this->callScriptSafe(
                $obj['scriptpath'],
                $obj['divisor']
            );
        }
        // Filter the result.
        return $this->applyFilter($objects, $params['start'], $params['limit'],
            $params['sortfield'], $params['sortdir']);
    }

    public function getSensor($params, $context)
    {
        // Validate the RPC caller context.
        $this->validateMethodContext($context, ["role" => OMV_ROLE_ADMINISTRATOR]);
        // Validate the parameters of the RPC service method.
        $this->validateMethodParams($params, "rpc.common.objectuuid");
        // Get the configuration object.
        $db = \OMV\Config\Database::getInstance();
        return $db->getAssoc("conf.service.tempmon.sensor", $params['uuid']);
    }

    public function setSensor($params, $context)
    {
        // Validate the RPC caller context.
        $this->validateMethodContext($context, ["role" => OMV_ROLE_ADMINISTRATOR]);
        // Validate the parameters of the RPC service method.
        $this->validateMethodParams($params, "rpc.tempmon.setsensor");
        // Prepare the configuration object.
        $object = new \OMV\Config\ConfigObject("conf.service.tempmon.sensor");
        $object->setAssoc($params);
        // Set the configuration object.
        $isNew = $object->isNew();
        $db = \OMV\Config\Database::getInstance();
        if ($isNew === true) {
            // Check uniqueness - Shared folder
            $db->assertIsUnique($object, "name");
            $db->assertIsUnique($object, "scriptpath");
        }
        $db->set($object);
        // Return the configuration object.
        return $object->getAssoc();
    }

    public function deleteSensor($params, $context)
    {
        // Validate the RPC caller context.
        $this->validateMethodContext($context, ["role" => OMV_ROLE_ADMINISTRATOR]);
        // Validate the parameters of the RPC service method.
        $this->validateMethodParams($params, "rpc.common.objectuuid");
        // Delete the configuration object.
        $db = \OMV\Config\Database::getInstance();
        $object = $db->get("conf.service.tempmon.sensor", $params['uuid']);
        $db->delete($object);
        // Return the deleted configuration object.
        return $object->getAssoc();
    }

    public function getAll($params, $context)
    {
        $this->validateMethodContext($context, ["role" => OMV_ROLE_EVERYONE]);
        $db = \OMV\Config\Database::getInstance();
        $objects = $db->getAssoc("conf.service.tempmon.sensor");
        $result = [];
        foreach ($objects as $obj) {
            try {
                $result[$obj['uuid']] = $this->callScript(
                    $obj['scriptpath'],
                    $obj['divisor']
                );
            } catch (\Exception $e) {
                $result[$obj['uuid']] = 0;
            }
        }
        return $result;
    }

    private function callScript($scriptPath, $divisor)
    {
        if ($divisor <= 0) {
            $divisor = 1;
        }
        $cmd = new \OMV\System\Process($scriptPath);
        $cmd->execute($output, $exitStatus);
        return intval($output[0]) / $divisor;
    }

    private function callScriptSafe($scriptPath, $divisor)
    {
        try {
            return number_format(
                $this->callScript($scriptPath, $divisor),
                1
            ) . " °C";
        } catch (\Exception $e) {
            return "-";
        }
    }
}
