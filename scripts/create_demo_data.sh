#!/usr/bin/env bash
set -euo pipefail

DEMOPATH="data/demo"
SEEDPATH="data/seeds"
QRELSPATH="data/qrels"
mkdir -p "$DEMOPATH" "$SEEDPATH" "$QRELSPATH"

# topic arrays
fr=("subjonctif" "passé composé" "imparfait" "articles" "pronoms" "conditionnel" "futur" "négation" "accord" "vocabulaire")
zh=("虚拟式" "复合过去时" "未完成过去时" "冠词" "代词" "条件式" "将来时" "否定" "配合一致" "词汇")
en=("subjunctive" "passe compose" "imparfait" "articles" "pronouns" "conditional" "future tense" "negation" "agreement" "vocabulary")

# ========== corpus ==========
CORPUS="$DEMOPATH/demo_corpus.jsonl"
> "$CORPUS"
for ((i=1;i<=100;i++)); do
  t=$(( (i-1) % 10 ))
  case $(( i % 3 )) in
    1) lang=fr; term=${fr[$t]}; title="FR: ${term}"; content="Ce document traite de ${term} en français. Exemples et règles essentielles." ;;
    2) lang=zh; term=${zh[$t]}; title="ZH: ${term}"; content="本文介绍法语${term}的用法与例句，含基本规则。" ;;
    0) lang=en; term=${en[$t]}; title="EN: ${term}"; content="This document covers French ${term} with rules and examples." ;;
  esac
  printf -v did "doc_%04d" "$i"
  printf '{"doc_id":"%s","title":"%s","content":"%s","text":"%s","language":"%s"}\n' "$did" "$title" "$content" "$content" "$lang" >> "$CORPUS"
done
echo "[demo] Wrote $CORPUS"

# ========== seeds ==========
SEEDS="$SEEDPATH/align_seeds.tsv"
echo -e "source_id\ttarget_id\tconfidence" > "$SEEDS"
for ((i=0;i<50;i++)); do
  t=$(( i % 10 ))
  printf "%s\t%s\t0.95\n" "${zh[$t]}" "${fr[$t]}" >> "$SEEDS"
done
echo "[demo] Wrote $SEEDS"

# ========== queries ==========
QUERIES="$QRELSPATH/queries.tsv"
echo -e "query_id\tquery_text\tlanguage" > "$QUERIES"
for ((i=1;i<=100;i++)); do
  t=$(( (i-1) % 10 ))
  case $(( i % 3 )) in
    1) lang=fr; qtext="${fr[$t]} français" ;;
    2) lang=zh; qtext="${zh[$t]} 用法" ;;
    0) lang=en; qtext="French ${en[$t]} usage" ;;
  esac
  printf "q%d\t%s\t%s\n" "$i" "$qtext" "$lang" >> "$QUERIES"
done
echo "[demo] Wrote $QUERIES"

# ========== qrels ==========
QRELS="$QRELSPATH/test.qrels"
> "$QRELS"
for ((i=1;i<=100;i++)); do
  t=$(( (i-1) % 10 ))
  doc1=$(( t+1 ))
  doc2=$(( t+11 ))
  doc3=$(( t+21 ))
  printf -v d1 "doc_%04d" "$doc1"
  printf -v d2 "doc_%04d" "$doc2"
  printf -v d3 "doc_%04d" "$doc3"
  printf "q%d 0 %s 1\n" "$i" "$d1" >> "$QRELS"
  printf "q%d 0 %s 1\n" "$i" "$d2" >> "$QRELS"
  printf "q%d 0 %s 1\n" "$i" "$d3" >> "$QRELS"
done
echo "[demo] Wrote $QRELS"

echo "Demo dataset generated."

