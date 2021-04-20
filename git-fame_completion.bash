_git_fame()
{
  local cur prv
  cur="${COMP_WORDS[COMP_CWORD]}"
  prv="${COMP_WORDS[COMP_CWORD-1]}"
  case ${COMP_CWORD} in
    1)
      COMPREPLY=($(compgen -W "fame" ${cur}))
      ;;
    *)
      case ${prv} in
        --sort)
          COMPREPLY=($(compgen -W 'loc commits files hours months' -- ${cur}))
          ;;
        --cost)
          COMPREPLY=($(compgen -W 'months cocomo hours commits' -- ${cur}))
          ;;
        --loc)
          COMPREPLY=($(compgen -W 'surviving insertions deletions' -- ${cur}))
          ;;
        --format)
          COMPREPLY=($(compgen -W 'pipe markdown yaml json csv tsv tabulate' -- ${cur}))
          ;;
        --log)
          COMPREPLY=($(compgen -W 'FATAL CRITICAL ERROR WARNING INFO DEBUG NOTSET' -- ${cur}))
          ;;
        --branch)
          COMPREPLY=($(compgen -W "$(git branch | sed 's/*/ /')" -- ${cur}))
          ;;
        --manpath)
          COMPREPLY=($(compgen -d -- ${cur}))
          ;;
        --incl|--excl|--since)
          COMPREPLY=( )
          ;;
        *)
          if [ ${COMP_WORDS[1]} == fame ]; then
            COMPREPLY=($(compgen -dW '-h --help -v --version --cost --branch --since --sort --loc --incl --excl -R --recurse -n --no-regex -s --silent-progress --warn-binary -t --bytype -w --ignore-whitespace -e --show-email --enum -M -C --format --manpath --log' -- ${cur}))
          fi
          ;;
      esac
      ;;
  esac
}
complete -F _git_fame git-fame
