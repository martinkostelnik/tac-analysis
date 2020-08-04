<?php

/**
 * File: test.php
 * Title: IPP Project 2
 * Author: Martin Kostelník (xkoste12)
 * Date: 14.5.2020
 * 
 */

$testDir = getcwd();
$parse = getcwd() . '/parse.php';
$interpret = getcwd() . '/interpret.py';
$jexamxml = '/pub/courses/ipp/jexamxml/jexamxml.jar';

$settings = array('--recursive' => false,
                  '--parse-only' => false,
                  '--int-only' => false);

$testsPassed = 0;

function parseArgs()
{
    global $argc, $argv, $settings;

    $counter = 0;

    if ($argc === 1)
    {
        return;
    }
    else if (in_array('-h', $argv) || in_array('--help', $argv))
    {
        if ($argc > 2)
        {
            fwrite(STDERR, "ERROR: Parameter -h or --help cannot be combined with other parameters\n");
            exit(10);
        }
        else
        {
            printHelp();
            exit(0);
        }
    }
    else
    {
        foreach ($argv as $key => $arg)
        {
            if (substr($arg, 0, strlen('--directory=')) === '--directory=')
            {
                $testDir = substr($argv[$key], strlen('--directory='));
                $counter++;
            }
            else if (substr($arg, 0, strlen('--parse-script=')) === '--parse-script=')
            {
                if (in_array('--int-only', $argv))
                {
                    fwrite(STDERR, "ERROR: --parse-script can not be combined with --int-only\n");
                    exit(10);
                }

                $parse = substr($argv[$key], strlen('--parse-script='));
                $counter++;
            }
            else if (substr($arg, 0, strlen('--int-script=')) === '--int-script=')
            {
                if (in_array('--parse-only', $argv))
                {
                    fwrite(STDERR, "ERROR: --int-script can not be combined with --parse-only\n");
                    exit(10);
                }

                $interpret = substr($argv[$key], strlen('--int-script='));
                $counter++;
            }
            else if (substr($arg, 0, strlen('--jexamxml=')) === '--jexamxml=')
            {
                $jexamxml = substr($argv[$key], strlen('--jexamxml='));
                $counter++;
            }
        }
        
        if (in_array('--recursive', $argv))
        {
            $settings['--recursive'] = true;
            $counter++;
        }

        if (in_array('--parse-only', $argv))
        {
            $settings['--parse-only'] = true;
            $counter++;
        }

        if (in_array('--int-only', $argv))
        {
            if ($settings['--parse-only'])
            {
                fwrite(STDERR, "ERROR: Can not combine --parse-only parameter with --int-only parameter\n");
                exit(10);
            }

            $settings['--int-only'] = true;
            $counter++;
        }

        if ($counter !== $argc - 1)
        {
            fwrite(STDERR, "ERROR: unknown parameters\n");
            exit(10);
        }
    }
}

function printHelp()
{
    echo "Skript test.php slouzi pro automaticke testovani aplikaci parse.php a interpret.py. Skript projde zadany adresar s testy a vyuzije je pro automaticke otestovani spravne funkcnosti obou predchozich programu a vygeneruje prehledny souhrn v HTML 5 do standardniho vystupu.\n";
}

function generateHead()
{
    echo "<!DOCTYPE HTML>";
	echo "<html>";
	echo "<head>";
	echo "<meta charset=\"utf-8\">";
	echo "<meta name=\"viewport\" content=\"width=1920, initial-scale=1.0\">";
	echo "<title>IPP project</title>";
	echo "</head>";
	echo "<body>";
}

function findTests($d)
{
    global $settings;

    $tests = array();

    if (is_dir($d)) // Check if $d is a directory
    {
        if ($handle = opendir($d)) // Try to open directory $d
        {
            while ($file = readdir($handle)) // iterate over all directories and files in $d
            {
                if ($file === '.' || $file === '..')
                {
                    continue;
                }
                else if(is_dir($d . "/" . $file) && $settings['--recursive'] === TRUE) // if a current file is a directory, skip or initiate recursion
                {
                    $tests = array_merge($tests, findTests($d . "/" . $file));
                }
                else
                {
                    if (pathinfo($file, PATHINFO_EXTENSION) === 'src')
                    {
                        $path = $d . "/" . basename($file, ".src");

                        array_push($tests, $path);

                        if (!is_file($path . ".out"))
                        {
                            shell_exec("touch " . $path . ".out");
                        }
                        if (!is_file($path . ".in"))
                        {
                            shell_exec("touch " . $path . ".in");
                        }
                        if (is_file($path . ".rc"))
                        {
                            shell_exec("touch " . $path . ".rc");
                        }
                        else
                        {
                            shell_exec("touch " . $path . ".rc");
                            shell_exec("echo '0' > " . $path . ".rc");
                        }
                    }
                }
            }

            closedir($handle);
            return $tests;
        }
        else
        {
            fwrite(STDERR, "ERROR: could not open test directory\n");
            exit(11);
        }
    }
    else
    {
        fwrite(STDERR, "ERROR: test directory is not a directory");
        exit(11);
    }
}

function runTest($i, $f)
{
    global $testsPassed, $settings, $parse, $interpret;

    echo "<br><br>TEST $i $f <br>";

    shell_exec('touch ./tmpParse');
    shell_exec('touch ./tmpInterpret');


    if ($settings['--int-only'] === FALSE)
    {
        exec('php7.4 ' . $parse . ' < ' . $f . '.src' . ' > ./tmpParse', $o, $rc);

        $refRC = shell_exec('cat ' . $f . '.rc');

        if ((int)$rc !== 0 && (int)$refRC !== (int)$rc)
        {
            echo "FAIL: rc of parse.php does not match. EXPECTED: $refRC   IS: $rc <br>";
            shell_exec('rm -rf ./tmpParse');
            shell_exec('rm -rf ./tmpInterpret');
            return;
        }
        if ($settings['--parse-only'] === TRUE && (int)$rc === 0)
        {
            exec('java -jar ' . $jexamxml . ' ' . $f . '.out ./tmpParse /D', $oo, $rrc);
            if (!empty($oo))
            {
                echo "FAIL: XML does not match <br>";
                shell_exec('rm -rf ./tmpParse');
                shell_exec('rm -rf ./tmpInterpret');
                return;
            }
        }
    }

    if ($settings['--parse-only'] === FALSE)
    {
        if ($settings['--int-only'] === FALSE)
        {
            exec('python3.8 ' . $interpret . ' --source=./tmpParse < ' . $f . '.in > ./tmpInterpret', $o, $rc);
        }
        else
        {
            exec('python3.8 ' . $interpret . ' --source=' . $f . '.src < ' . $f . '.in > ./tmpInterpret', $o, $rc);
        }

        if ((int)$refRC !== (int)$rc)
        {
            echo "FAIL: rc of interpret.py does not match. EXPECTED: $refRC   IS: $rc <br>";
            shell_exec('rm -rf ./tmpParse');
            shell_exec('rm -rf ./tmpInterpret');
            return;
        }

        if ((int)$rc === 0)
        {
            exec("diff ./tmpInterpret " . $f . ".out", $oo, $rc);
            if (!empty($oo))
            {
                echo "FAIL: output of intepret.py and .out does not match <br>";
                shell_exec('rm -rf ./tmpParse');
                shell_exec('rm -rf ./tmpInterpret');
                return;
            }
        }
    }

    shell_exec('rm -rf ./tmpParse');
    shell_exec('rm -rf ./tmpInterpret');
    echo "OK<br>";
    $testsPassed++;
}

function writeStats($total)
{
    global $testsPassed;
    echo "<br>Total tests:\t$total  <br>";
    echo "Tests passed:\t$testsPassed <br>";
    echo "Tests failed:\t" . (string)($total - $testsPassed) . "<br>";
}

function main()
{
    global $testDir, $parse, $interpret, $jexamxml, $settings, $testsPassed;

    parseArgs();
    generateHead();

    $tests = findTests($testDir);

    foreach ($tests as $key => $test)
    {
        runTest($key, $test);
    }

    writeStats(count($tests));
    
    echo "</body>";
    echo "</html>";
}

main();

?>
