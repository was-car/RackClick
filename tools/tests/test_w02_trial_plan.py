"""Pruebas estaticas del ejecutor W-02 (tools/windows/w02/Invoke-W02TrialPlan.ps1).

No ejecutan PowerShell ni tocan el host. Comprueban que los pins del ejecutor coinciden con la entrega 08,
que las compuertas de Execute van antes del lanzamiento del envoltorio, que el procedimiento 08 nombra los 15 campos
del validador oficial y que el ejecutor es ASCII puro (Windows PowerShell 5.1 lee sin BOM como ANSI).
El procedimiento 07 queda como historia y sus pruebas siguen apuntando a el.
"""
import re
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / 'tools' / 'windows' / 'w02' / 'Invoke-W02TrialPlan.ps1'
PROCEDURE = ROOT / 'docs' / 'PROCEDIMIENTO-W02-NEW-RESTORE-07.md'
PROCEDURE_08 = ROOT / 'docs' / 'PROCEDIMIENTO-W02-RESTORE-08.md'
SETUP = ROOT / 'tools' / 'windows' / 'server-install' / 'RackClick.Setup.ps1'
DELIVERY = ROOT / '.local' / 'instalador-08-codex' / 'entrega'
PLAN_FIELDS = ['schemaVersion', 'id', 'bindAddress', 'publicHost', 'httpsPort', 'postgresPort', 'allowedSubnet',
               'systemhaus', 'bootstrapUser', 'serviceName', 'accountName', 'mode', 'backupPath',
               'backupManifestSha256', 'trustOnServer']


class TrialRunnerStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = RUNNER.read_text(encoding='utf-8')

    def test_runner_is_plain_ascii_for_windows_powershell_51(self):
        self.assertEqual([c for c in self.source if ord(c) > 127], [])

    def test_pins_are_the_08_delivery_hashes(self):
        pins = dict(re.findall(r"'(RackClick-[^']+\.zip)'='([0-9a-f]{64})'", self.source))
        self.assertEqual(len(pins), 4)
        for name, digest in pins.items():
            with self.subTest(file=name):
                self.assertIn(name, self.source)
        sums = DELIVERY / 'SHA256SUMS.txt'
        if sums.exists():
            # Acepta el formato de la entrega 07 (" *nombre") y el de la 08 ("  nombre", CRLF).
            listed = {}
            for line in sums.read_text(encoding='ascii').splitlines():
                m = re.match(r'([0-9a-f]{64}) [ *](.+)$', line.strip())
                if m:
                    listed[m.group(2)] = m.group(1)
            for name, digest in pins.items():
                with self.subTest(file=name):
                    self.assertEqual(listed[name], digest)

    def test_payload_json_pin_matches_the_payload_inside_the_archive(self):
        match = re.search(r"\$PayloadJsonSha='([0-9a-f]{64})'", self.source)
        self.assertIsNotNone(match)
        payload = DELIVERY / 'RackClick-Servidor-08-payload.zip'
        if not payload.exists():
            self.skipTest('requiere la entrega 08 en .local')
        import hashlib
        with zipfile.ZipFile(payload) as archive:
            data = archive.read('RackClick-Instalador/payload.json')
        self.assertEqual(hashlib.sha256(data).hexdigest(), match.group(1))

    def test_execute_gates_run_in_order_before_the_official_launcher(self):
        body = self.source[self.source.index('function Invoke-W02Execute'):]
        order = ['execute_host_excluded', 'execute_host_not_allowlisted', 'execute_confirmation_mismatch',
                 'execute_check_not_passed']
        positions = [body.index("'" + code + "'") for code in order]
        self.assertEqual(positions, sorted(positions))
        plan = body.index('$plan=Invoke-W02Plan')
        check = body.index('Invoke-W02Check ([int]$plan.httpsPort)')
        lock = body.index('$locks=Lock-W02WrapperFiles $auth')
        verify = body.index("'-VerifyOnly'")
        reverify = body.index('Assert-W02LockedFiles $locks $auth')
        launch = body.index('$run=Start-Process')
        self.assertLess(positions[2], plan)
        self.assertLess(plan, check)
        self.assertLess(check, positions[3])
        self.assertLess(positions[3], lock)
        self.assertLess(lock, verify)
        self.assertLess(verify, reverify)
        self.assertLess(reverify, launch)

    def test_verified_files_stay_locked_read_only_across_both_launches(self):
        # R1b: los ficheros validados se abren solo para lectura y sin compartir escritura ni borrado.
        self.assertIn('[IO.FileShare]::Read', self.source)
        self.assertIn('[IO.FileAccess]::Read', self.source)
        # Solo el bloqueo de los ficheros del envoltorio: el temporal del recibo se escribe en exclusiva a proposito.
        bloqueo = self.source[self.source.index('function Lock-W02WrapperFiles'):self.source.index('function Assert-W02LockedFiles')]
        for forbidden in ['FileShare]::ReadWrite', 'FileShare]::Write', 'FileShare]::Delete', 'FileShare]::None']:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, bloqueo)
        body = self.source[self.source.index('function Invoke-W02Execute'):]
        self.assertGreaterEqual(body.count('Assert-W02LockedFiles $locks $auth'), 1)
        self.assertIn('foreach($lock in $locks){$lock.stream.Dispose()}', body)

    def test_execute_no_longer_trusts_a_local_plan_report(self):
        # Un plan-report.json previo y coherente no puede sustituir a la validacion de la hoja (R2).
        self.assertNotIn('planReportPath', self.source)
        self.assertNotIn('execute_plan_not_validated', self.source)

    def test_wrapper_is_bound_to_the_official_zip_and_its_authentic_package(self):
        match = re.search(r"\$PackageJsonSha='([0-9a-f]{64})'", self.source)
        self.assertIsNotNone(match)
        wrapper = DELIVERY / 'RackClick-Servidor-08.zip'
        if wrapper.exists():
            with zipfile.ZipFile(wrapper) as archive:
                package = archive.read('RackClick-Servidor-08/PAQUETE.json')
            import hashlib
            self.assertEqual(hashlib.sha256(package).hexdigest(), match.group(1))
        for code in ['execute_wrapper_package_mismatch', 'execute_wrapper_files_unlisted',
                     'execute_wrapper_hash_mismatch', 'execute_wrapper_reparse_not_allowed']:
            with self.subTest(code=code):
                self.assertIn("'" + code + "'", self.source)

    def test_plan_text_diagnostics_are_structured_and_precede_the_validator(self):
        for code in ['plan_json_invalid', 'plan_field_control_character', 'plan_field_invalid_path_character']:
            with self.subTest(code=code):
                self.assertIn("'" + code + "'", self.source)
        self.assertLess(self.source.index('Assert-W02PlanText $planFull'), self.source.index('Read-SetupPlan $planFull'))

    def test_excluded_hosts_are_declared(self):
        self.assertIn("ExcludedComputerName=@('LEAO')", self.source)
        self.assertIn("ExcludedAddress=@('192.168.250.78')", self.source)

    def test_plan_fields_match_the_official_validator(self):
        setup = SETUP.read_text(encoding='utf-8')
        match = re.search(r"\$expected=@\(([^)]*)\)", setup)
        self.assertIsNotNone(match)
        validator = re.findall(r"'([A-Za-z0-9]+)'", match.group(1))
        self.assertEqual(validator, PLAN_FIELDS)


class TrialProcedureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PROCEDURE.read_text(encoding='utf-8')

    def test_procedure_names_each_of_the_fifteen_plan_fields(self):
        for field in PLAN_FIELDS:
            with self.subTest(field=field):
                self.assertIn('`' + field + '`', self.text)

    def test_procedure_states_the_real_artifact_hashes(self):
        for digest in ['3ca223230fc5ea1ab1e2ce7e40c9b7ca222ef65e4735412cb3fdb7cfd19ddca1',
                       '71469d1e084fe1927eadfc2122540868c1db8bf9ac1d22f8819574e4afef8d37',
                       '6d5a3896422c308e6b086822aaaa76a5fb6cc2584cf0664666f96504709e14f8',
                       'b36fd6d394f090d4fcbc16fa7c278132486a58ed8c774199b5001ea0030703bd',
                       '25a764a9fa40f0e8feb39cfbc9b2b3f1f21bb1137738edd53614b257f6277ec7']:
            with self.subTest(digest=digest[:12]):
                self.assertIn(digest, self.text)

    def test_procedure_reboot_opens_the_verification_cmd_of_this_edition_not_install_again(self):
        self.assertIn('awaiting_reboot', self.text)
        self.assertIn('Verificar instalacion', self.text)
        self.assertNotIn('Verificar instalación', self.text)
        self.assertNotIn('reinicio no se reanuda por sí solo', self.text)
        self.assertIn('RackClick-VERIFICAR-05-', self.text)
        self.assertIn('Escritorio', self.text)
        self.assertIn('esta edición 07', self.text)
        self.assertNotIn('reabrir el instalador', self.text.lower())
        self.assertIn('no se vuelve a ejecutar Execute', self.text)

    def test_procedure_states_plan_json_error_has_no_field(self):
        self.assertIn('plan_json_invalid', self.text)
        self.assertIn('no identifica campo', self.text)

    def test_procedure_generates_uuid_apart_and_compares_the_other_fourteen_fields(self):
        self.assertIn('UUID', self.text)
        self.assertIn('14 campos', self.text)

    def test_procedure_restore_uses_vm_b_own_addresses_and_repeats_reboot_and_report(self):
        self.assertIn('VM B', self.text)
        self.assertIn('bindAddress', self.text)
        self.assertIn('publicHost', self.text)
        self.assertIn('5.5 a 5.7', self.text)

    def test_procedure_export_requires_local_ntfs_and_export_complete(self):
        self.assertIn('NTFS', self.text)
        self.assertIn('export_complete', self.text)

    def test_procedure_keeps_the_trial_pending_and_says_so(self):
        self.assertIn('pendiente', self.text.lower())
        for sub in ['W-02.01', 'W-02.02', 'W-02.03', 'W-02.04', 'W-02.05']:
            self.assertIn(sub, self.text)


class R3ContractTests(unittest.TestCase):
    # W-02-R3: recibo de inicio antes de la primera llamada, fases con salida observada y recogida de solo lectura.
    @classmethod
    def setUpClass(cls):
        cls.source = RUNNER.read_text(encoding='utf-8')
        cls.body = cls.source[cls.source.index('function Invoke-W02Execute'):]

    def test_receipt_is_published_before_the_first_wrapper_call(self):
        self.assertIn("Publish-W02File $runDir 'recibo-inicio.json'", self.body)
        self.assertLess(self.body.index("'recibo-inicio.json'"), self.body.index("'-VerifyOnly'"))

    def test_phases_are_published_with_observed_exit_codes(self):
        for fase in ['fase-02-verify.json', 'fase-03-interactiva-inicio.json', 'fase-04-interactiva-fin.json']:
            with self.subTest(fase=fase):
                self.assertIn(fase, self.body)
        self.assertIn('exitCode=$run.ExitCode', self.body)
        self.assertLess(self.body.index("'fase-03-interactiva-inicio.json'"), self.body.index('$run=Start-Process'))

    def test_publication_is_new_and_atomic(self):
        publish = self.source[self.source.index('function Publish-W02File'):self.source.index('function Get-W02BootUtc')]
        self.assertIn('[IO.FileMode]::CreateNew', publish)
        self.assertIn('[IO.File]::Move($tmp,$final)', publish)
        self.assertIn("throw 'w02_publish_exists'", publish)

    def test_reconcile_never_launches_anything(self):
        reconcile = self.source[self.source.index('function Invoke-W02Reconcile'):self.source.index('function Invoke-W02Execute')]
        for prohibido in ['Start-Process', 'Invoke-W02Execute', 'Invoke-W02Plan', 'Invoke-W02Check', 'Lock-W02WrapperFiles']:
            with self.subTest(prohibido=prohibido):
                self.assertNotIn(prohibido, reconcile)
        self.assertIn("'Reconcile'", self.source)

    def test_preboot_result_is_only_read_never_written(self):
        reconcile = self.source[self.source.index('function Invoke-W02Reconcile'):self.source.index('function Invoke-W02Execute')]
        self.assertNotIn('Set-Content', reconcile)
        self.assertNotIn('Out-File', reconcile)
        self.assertNotIn('WriteAllText', reconcile)


class R3bContractTests(unittest.TestCase):
    # W-02-R3b (devolucion de Codex): salida nativa y validacion separadas, contratos del recibo, seleccion por
    # fecha, diagnosticos por intento y postboot vinculado.
    @classmethod
    def setUpClass(cls):
        cls.source = RUNNER.read_text(encoding='utf-8')
        cls.body = cls.source[cls.source.index('function Invoke-W02Execute'):]
        cls.reconcile = cls.source[cls.source.index('function Invoke-W02Reconcile'):cls.source.index('function Invoke-W02Execute')]

    def test_native_exit_and_json_validation_are_separate_phases(self):
        self.assertIn("'fase-02b-validacion.json'", self.body)
        self.assertLess(self.body.index("'fase-02-verify.json'"), self.body.index("'fase-02b-validacion.json'"))
        self.assertIn('validez_desconocida', self.reconcile)
        self.assertIn('execute_verify_unreadable', self.body)

    def test_receipt_contract_is_checked_before_any_state_is_reported(self):
        for pieza in ['Get-W02ReceiptProblems', 'Test-W02Guid', 'ConvertTo-W02Utc', 'Test-W02Hex', 'secuencia_incoherente', 'contrato_incoherente']:
            with self.subTest(pieza=pieza):
                self.assertIn(pieza, self.source)

    def test_latest_attempt_is_chosen_by_start_time_not_by_name(self):
        self.assertIn('Sort-Object utc -Descending', self.reconcile)
        self.assertIn('ultimoIntentoRunId', self.reconcile)
        self.assertIn('seleccion_ambigua', self.reconcile)
        self.assertNotIn('Sort-Object Name | Select', self.reconcile)

    def test_verification_diagnostics_live_inside_each_attempt_folder(self):
        self.assertIn("$verifyOut=Join-Path $runDir 'execute-verify-salida.json'", self.body)
        self.assertNotIn("$verifyOut=Join-Path $OutputDirectory", self.body)

    def test_postboot_is_linked_to_installation_and_current_boot(self):
        for estado in ['postboot_desfasado', 'postboot_de_otra_instalacion', 'postboot_verificado_vinculo_parcial', 'vinculo_incompleto']:
            with self.subTest(estado=estado):
                self.assertIn(estado, self.reconcile)

    def test_reconcile_still_never_launches_or_writes_preboot(self):
        for prohibido in ['Start-Process', 'Invoke-W02Execute', 'Invoke-W02Plan', 'Invoke-W02Check', 'Lock-W02WrapperFiles', 'Set-Content', 'Out-File', 'WriteAllText']:
            with self.subTest(prohibido=prohibido):
                self.assertNotIn(prohibido, self.reconcile)

    def test_phase_sequence_is_judged_as_a_whole_before_any_state_is_reported(self):
        # Una fase 02 distinta de cero no puede seguir a 02b, 03 o 04 (R8). El veredicto se calcula antes de clasificar.
        for pieza in ['Get-W02PhaseVerdict', 'fase02_distinta_de_cero_con_continuacion', 'fase03_sin_validacion_positiva', 'orden_fase02_fase02b']:
            with self.subTest(pieza=pieza):
                self.assertIn(pieza, self.source)
        self.assertLess(self.reconcile.index('Get-W02PhaseVerdict $f02'), self.reconcile.index("$e.estado='exit_observado'"))

    def test_postboot_contract_is_checked_before_any_linkage_state(self):
        # Un postboot contradictorio no puede llegar a verificado ni a otra instalacion (R9).
        self.assertIn('Get-W02PostbootProblems', self.source)
        self.assertIn('postboot_contrato_incoherente', self.reconcile)
        self.assertLess(self.reconcile.index('Get-W02PostbootProblems $p'), self.reconcile.index("'postboot_de_otra_instalacion'"))
        self.assertLess(self.reconcile.index('Get-W02PostbootProblems $p'), self.reconcile.index("$post.estado='postboot_verificado_vinculo_parcial'"))

    def test_registered_verification_is_kept_apart_from_current_health_and_pins_do_not_authenticate(self):
        self.assertIn("saludActual='no_comprobada_por_reconcile'", self.reconcile)
        self.assertIn('verificacionRegistrada', self.reconcile)
        self.assertIn('no autentican', self.reconcile)


class Edition08ReferenceTests(unittest.TestCase):
    # Referencia de la edicion 08: el ejecutor, Reconcile y el procedimiento de C usan solo los nombres y pins 08.
    @classmethod
    def setUpClass(cls):
        cls.source = RUNNER.read_text(encoding='utf-8')
        cls.procedure = PROCEDURE_08.read_text(encoding='utf-8')

    def test_no_literal_07_names_or_pins_remain_in_the_runner(self):
        self.assertNotIn('RackClick-Servidor-07', self.source)
        self.assertNotIn('RackClick-Cambiar-IP-07', self.source)
        self.assertNotIn('RackClick-Bundle-M3-14-07', self.source)
        self.assertNotIn("edition -cne '07'", self.source)

    def test_reconcile_compares_the_wrapper_reference_through_the_current_key(self):
        self.assertIn('$Pins[$WrapperZipName]', self.source)
        self.assertNotIn("$Pins['RackClick-Servidor-07.zip']", self.source)

    def test_envelope_edition_is_checked_against_the_08_edition(self):
        self.assertIn("$envelope.edition -cne '08'", self.source)

    def test_restore_08_procedure_names_each_of_the_fifteen_plan_fields(self):
        for field in PLAN_FIELDS:
            with self.subTest(field=field):
                self.assertIn('`' + field + '`', self.procedure)

    def test_restore_08_procedure_states_the_08_artifact_hashes(self):
        for digest in ['2855898161ed94ff36fba73b11ac2bb02e9b4d9702e4af6976e946a7307561ae',
                       'f1988ba75ef8f278b5d64b81d7a8fb02d99a3be451e8ce70e2f97a4452538da4',
                       'a26856cb2bf3b9ed76384ebfe40fcc1587075708d3383e6b515246bfebb6da6f',
                       'c070fa06cf40808e0d43197da743bed52c00361ce05f45549ff6498b3a36c6c8',
                       '0d9df32b11a1c39df66cbb444739628eb8f867b06f55d2b3b3e45681ee29baa6',
                       '1f362949398b3da539a171b1150270599fa1761a0c7e1a7649aff31bc68972ac']:
            with self.subTest(digest=digest[:12]):
                self.assertIn(digest, self.procedure)

    def test_restore_08_procedure_is_for_vm_c_and_keeps_the_historic_label_and_stays_unrun(self):
        for pieza in ['VM C', 'w02-recovery-c', 'RackClickSvcC', 'RackClick-VERIFICAR-05-', 'no ejecutar', '14 campos', 'UUID']:
            with self.subTest(pieza=pieza):
                self.assertIn(pieza, self.procedure)
        self.assertNotIn('RackClick-Servidor-07', self.procedure)


class FocusBatteryTests(unittest.TestCase):
    # La bateria de focos debe fallar de verdad: codigo de salida no cero ante cualquier caso fallido o lanzamiento.
    @classmethod
    def setUpClass(cls):
        cls.battery = (ROOT / 'evidence' / 's1-20261025' / 'w02-vm-limpia-07-claude' / 'focos' / 'ejecutar-focos.sh').read_text(encoding='utf-8')
        cls.generator = (ROOT / 'evidence' / 's1-20261025' / 'w02-vm-limpia-07-claude' / 'focos' / 'generar-focos.py').read_text(encoding='utf-8')

    def test_battery_exits_nonzero_on_any_failure_and_has_a_negative_switch(self):
        self.assertIn('BATERIA_FALLIDA', self.battery)
        self.assertIn('exit 1', self.battery)
        self.assertIn('W02_FOCOS_NEGATIVO', self.battery)
        self.assertIn('fallos=$((fallos+1))', self.battery)

    def test_battery_keeps_python_exit_code_and_checks_launches_after_the_cases(self):
        self.assertIn('estat_rc=$?', self.battery)
        self.assertLess(self.battery.index('for d in "$RUN"/out/w-*'), self.battery.index('BATERIA_OK'))
        self.assertIn('if [ "$comprobados" -eq 0 ]', self.battery)

    def test_battery_uses_a_new_directory_per_run_and_never_removes_with_a_shell(self):
        self.assertNotIn('rmdir', self.battery)
        self.assertIn('run-$(date', self.battery)
        self.assertIn('el directorio de ejecucion ya existe', self.generator)
        self.assertIn('os.makedirs(F + \'/planes\')', self.generator)


if __name__ == '__main__':
    sys.exit(unittest.main())
