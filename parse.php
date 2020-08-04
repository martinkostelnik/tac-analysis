<?php

/**
 * File: parse.php
 * Title: IPP Project 1
 * Author: Martin Kostelník (xkoste12)
 * Date: 11.3.2020
 * 
 */

/**
 * Global associative array for storing statistics
 *
 */
$stats = array('enabled'    => false,
               'index'      => 0,
               'path'       => '',
               'order'      => array(),
               'labels'     => array(),
               '--comments' => 0,
               '--loc'      => 0,
               '--labels'   => 0,
               '--jumps'    => 0);

/**
 * Function for command line argument parsing
 * 
 */
function parseArgs()
{
    global $argc, $argv, $stats;
    
    if ($argc == 1)
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
    else // STATS ARGUMENTS
    {
        foreach ($argv as $key => $arg)
        {
            if (substr($arg, 0, strlen('--stats=')) === '--stats=')
            {
                if ($stats['enabled'])
                {
                    fwrite(STDERR, "ERROR: You cannot specify --stats parameter more than once\n");
                    exit(10);
                }
                else
                {
                    $stats['enabled'] = true;
                    $stats['index'] = $key;
                    $stats['path'] = substr($argv[$key], 8);

                    foreach($argv as $key2 => $arg2)
                    {
                        if ($arg2 == '--loc' || $arg2 == '--comments' || $arg2 == '--labels' || $arg2 == '--jumps')
                        {
                            array_push($stats['order'], $arg2);
                        }
                        else if ($key2 === 0 || $key2 === $stats['index'])
                        {
                            continue;
                        }
                        else
                        {
                            fwrite(STDERR, "ERROR: Invalid arguments\n");
                            exit(10);
                        }
                    }
                }
            }
        }

        if (!$stats['enabled'] && $argc > 1)
        {
            fwrite(STDERR, "ERROR: Invalid arguments\n");
            exit(10);
        }
    }
}

/**
 * Helper function for printing help message when -h parameter is used
 * 
 */
function printHelp()
{
    echo "Skript typu filtr (parse.php v jazyce PHP 7.4) nacte ze standardniho vstupu zdrojovy kod v IPPcode20, zkontroluje lexikalni a syntaktickou spravnost kodu a vypise na standardni vystup XML reprezentaci programu.\n";
}

/**
 * This function reads code from STDIN and stores it in an array with lines as elements
 * 
 */
function readCode()
{
    $code = array();

    while ($line = fgets(STDIN))
    {
        array_push($code, $line);
    }

    if (count($code) === 0) // Check for empty source file
    {
        fprintf(STDERR, "ERROR: Header wrong or missing\n");
        exit(21);
    }

    return $code;
}

/**
 * Compares string with IPPcode20 header
 * 
 */
function checkHeader($line)
{
    $line = strtoupper($line);

    if ($line !== '.IPPCODE20')
    {
        fprintf(STDERR, "ERROR: Header wrong or missing\n");
        exit(21);
    }
}

/**
 * This function is used in code formatting.
 * String with current line get passed and if it contains a comment, the comment gets removed
 * 
 */
function removeComment(&$line)
{
    global $stats;

    if (($len = strpos($line, '#')) === FALSE) // line has no comment
    {
        return;
    }
    else
    {
        $line = substr($line, 0, $len);
        
        if ($len == 0) // append newline
        {
            $line .= "\n";
        }

        $stats['--comments']++;
    }
}

/**
 * Formats the code to simplify the analysis.
 * Removes whitespaces and replaces them with a single space (ASCII 32)
 * Removes comments
 * Removes empty lines
 * 
 */
function formatCode(&$input)
{
    global $stats;

    foreach ($input as $key => &$line)
    {
        $line = preg_replace('/\s+/', ' ', $line); // remove all whitespaces and replace them with single space
        $line = ltrim($line, ' '); // remove left space
        removeComment($line); // remove comment if present
        $line = rtrim($line, ' '); // remove right space

        if (!strcmp($line, "\n") || !strcmp($line, "")) // if line empty, remove it
        {
            unset($input[$key]);
        }
        
    }
    $input = array_values($input); // re-index array

    $stats['--loc'] = count($input) - 1;
}

/**
 * Checks variable syntax
 * 
 */
function isVar($s)
{
    $pattern = '/^[TGL]F@[a-zA-Z_\-$&%*!?][a-zA-Z\d_\-$&%*!?]*$/';

    return preg_match($pattern, $s);
}

/**
 * Checks label syntax
 * 
 */
function isLabel($s)
{
    $pattern = '/^[a-zA-Z_\-$&%*!?][a-zA-Z\d_\-$&%*!?]*$/';

    return preg_match($pattern, $s);
}

/**
 * Checks symbol syntax
 * 
 */
function isSymb($s)
{   
    $pattern = '/^(int@[+-]?(([1-9]\d*)|0))$|^(nil@nil)$|^(bool@(([tT][rR][uU][eE])|([fF][aA][lL][sS][eE])))$|^(string@)([^\s#\\\\]|(\\\\\d{3}))*$/';

    return isVar($s) || preg_match($pattern, $s);
}

/**
 * Checks type syntax
 * 
 */
function isType($s)
{
   return $s === 'int' || $s === 'bool' || $s === 'string' || $s === 'nil';
}

/**
 * Parsing function.
 * Receives a string (a line from formatted source code) and proceeds with lexical and syntax analysis
 * 
 */
function analyzeLine($line)
{
    global $stats;

    $instruction = explode(' ', $line);
    $instruction[0] = strtoupper($instruction[0]);

    switch ($instruction[0])
    {
        case 'RETURN':
            $stats['--jumps']++;
        case 'CREATEFRAME':
        case 'PUSHFRAME':
        case 'POPFRAME':
        case 'BREAK':
            if (count($instruction) !== 1)
            {
                fwrite(STDERR, "ERROR: Invalid operands\n");
                exit(23);
            }
            break;

        // <var> <symb>
        case 'MOVE':
        case 'INT2STR':
        case 'INT2CHAR':
        case 'STRLEN':
        case 'TYPE':
        case 'NOT':
            if (count($instruction) !== 3 || !isVar($instruction[1]) || !isSymb($instruction[2]))
            {
                fwrite(STDERR, "ERROR: Invalid operands\n");
                exit(23);
            }
            break;

        // <var>
        case 'DEFVAR':
        case 'POPS':
            if (count($instruction) !== 2 || !isVar($instruction[1]))
            {
                fwrite(STDERR, "ERROR: Invalid operands\n");
                exit(23);
            }
            break;

        // <label>
        case 'CALL':
        case 'JUMP':
            $stats['--jumps']++;
        case 'LABEL':
            if (count($instruction) !== 2 || !isLabel($instruction[1]))
            {
                fwrite(STDERR, "ERROR: Invalid operands\n");
                exit(23);
            }
            else if (!in_array($instruction[1], $stats['labels']) && $instruction[0] === 'LABEL')
            {
                $stats['--labels']++;
                array_push($stats['labels'], $instruction[1]);
            }
            break;

        // <symb>
        case 'PUSHS':
        case 'WRITE':
        case 'EXIT':
        case 'DPRINT':
            if (count($instruction) !== 2 || !isSymb($instruction[1]))
            {
                fwrite(STDERR, "ERROR: Invalid operands\n");
                exit(23);
            }
            break;

        // <var> <symb1> <symb2>
        case 'ADD':
        case 'SUB':
        case 'MUL':
        case 'IDIV':
        case 'LT':
        case 'GT':
        case 'EQ':
        case 'AND':
        case 'OR':
        case 'STRI2INT':
        case 'CONCAT':
        case 'GETCHAR':
        case 'SETCHAR':
            if (count($instruction) !== 4 || !isVar($instruction[1]) || !isSymb($instruction[2]) || !isSymb($instruction[3]))
            {
                fwrite(STDERR, "ERROR: Invalid operands\n");
                exit(23);
            }
            break;

        // <label> <symb1> <symb2>
        case 'JUMPIFEQ':
        case 'JUMPIFNEQ':
            $stats['--jumps']++;
            if (count($instruction) !== 4 || !isLabel($instruction[1]) || !isSymb($instruction[2]) || !isSymb($instruction[3]))
            {
                fwrite(STDERR, "ERROR: Invalid operands\n");
                exit(23);
            }
            break;

        // <var> <type>
        case 'READ':
            if (count($instruction) !== 3 || !isVar($instruction[1]) || !isType($instruction[2]))
            {
                fwrite(STDERR, "ERROR: Invalid operands\n");
                exit(23);
            }
            break;

        default:
            fwrite(STDERR, "ERROR: Unknown opcode\n");
            exit(22);
    }
}

/**
 * Function deduces the type of an operand and returns it
 * Operands at this point all have proper syntax
 * 
 */
function deduceType($operand, $isLabel, $k)
{
    $types = array('int', 'bool', 'string', 'nil', 'label', 'type');

    if (strpos($operand, '@') ==! false) // has @
    {
        $prefix = strtok($operand, '@');

        if (in_array($prefix, $types))
        {
            return $prefix;
        }
        else
        {
            return 'var';
        }
    }
    else
    {
        if ($isLabel && $k === 1)
        {
            return 'label';
        }
        else
        {
            return 'type';
        }
    }
}

/**
 * XML generating function
 * XMLWriter is used as a generator library
 * 
 */
function generateXML($code)
{
    global $types;   

    $xml = xmlwriter_open_memory();
    xmlwriter_set_indent($xml, 1);
    xmlwriter_set_indent_string($xml, '  ');

    xmlwriter_start_document($xml, '1.0', 'UTF-8');

    xmlwriter_start_element($xml, 'program');
    xmlwriter_write_attribute($xml, 'language', 'IPPcode20');

    $labelInstructions = array('LABEL', 'CALL', 'JUMP', 'JUMPIFEQ', 'JUMPIFNEQ');

    foreach ($code as $key => $line)
    {
        $line = explode(' ', $line);

        xmlwriter_start_element($xml, 'instruction');

        xmlwriter_write_attribute($xml, 'order', $key + 1);
        xmlwriter_write_attribute($xml, 'opcode', strtoupper($line[0]));

        $isLabel = False;

        foreach ($line as $k => $w)
        {
            if ($k === 0)
            {
                $isLabel = (in_array(strtoupper($w), $labelInstructions) ? True : False);
                continue;
            }

            xmlwriter_start_element($xml, 'arg' . $k);

            $delPos = strpos($w, '@');
            $type = deduceType($w, $isLabel, $k);

            xmlwriter_write_attribute($xml, 'type', $type);

            if ($type === 'bool')
                {
                xmlwriter_text($xml, strtolower(substr($w, $delPos + 1)));
            }
            else
            {
                xmlwriter_text($xml, $type === 'var' ? $w : ($delPos ==! false ? substr($w, $delPos + 1) : $w));
            }
            xmlwriter_end_element($xml);
        }

        xmlwriter_end_element($xml);
    }

    xmlwriter_end_element($xml);
    xmlwriter_end_document($xml);

    echo xmlwriter_output_memory($xml);
}

/**
 * Opens a file specified in the command line argument and writes statistics into it
 * 
 */
function writeStats()
{
    global $stats;

    $f = fopen($stats['path'], 'w');
    if (!$f)
    {
        fwrite(STDERR, "ERROR: could not open file\n");
        exit(12);
    }

    foreach ($stats['order'] as $par)
    {
        fwrite($f, $stats[$par] . "\n");
    }

    fclose($f);
}

function main()
{
    global $stats;

    parseArgs();
    
    $code = readCode();
    formatCode($code);

    checkHeader($code[0]);
    array_shift($code);

    foreach ($code as $line)
    {
        analyzeLine($line);
    }

    generateXML($code);

    if ($stats['enabled'])
    {
        writeStats();
    }
}

main();

?>
