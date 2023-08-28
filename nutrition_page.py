from flask import Flask, redirect, url_for, render_template, request
import pandas as pd
import numpy as np
#Функия для получения таблицы с именами, производителем, энтеральностью и доступностью веществ по заявленым тэгам
#Подкорректировать сиппинг
def get_by_tags (polim,caloric,special,vol,is_enternal, sip_tube):
    return (f"SELECT DISTINCT n0.id as nutrient_id, n0.name, n0.manufacturer, n0.is_enteral, n0.is_available FROM `nutrition` n0 INNER JOIN `nutrition_tagging` n1 ON n0.id = n1.nutrient_id and n1.tag_id in ({polim}) INNER JOIN `nutrition_tagging` n2 ON n1.nutrient_id = n2.nutrient_id and n2.tag_id in ({caloric}) INNER JOIN `nutrition_tagging` n3 ON n3.nutrient_id = n2.nutrient_id and n3.tag_id in ({special}) INNER JOIN `nutrition_tagging` n4 ON n4.nutrient_id = n3.nutrient_id and n4.tag_id in ({vol}) INNER JOIN `nutrition` n5 ON n0.name = n5.name and n5.is_enteral in ({is_enternal}) INNER JOIN `nutrition_tagging` n6 ON n4.nutrient_id = n6.nutrient_id and n6.tag_id in ({sip_tube});")

#Функия для получения таблицы со списокм всех тэгов, конкатенированных для каждого нутриента
def get_nutrient_tags ():
    return ('select n1.nutrient_id, GROUP_CONCAT(CONCAT(n2.tag)) as "all tags" from nutrition_tagging n1 INNER JOIN nutrition_tag n2 ON n1.tag_id=n2.id GROUP BY n1.nutrient_id;')

#Функия для получения таблицы пищевой и энергетической ценностей для каждого нутриента
def get_PFCE_mash_positive ():
    return ('select DISTINCT n2.nutrient_id, n1.id as feature_id, n1.name, n2.value from nutrition_feature n1 INNER JOIN nutrition_feature_value n2 on n1.id=n2.feature_id where id in (16, 46, 29, 49, 50, 51, 13, 48);')

def db_nutr_table_app(is_enternal,caloric,polim,sip_tube,special,vol):
    #from util_db_nutr import get_by_tags, get_nutrient_tags, get_PFCE_mash_positive
    import mysql.connector
    from mysql.connector import connect, Error
    import pandas as pd
    from pandas import DataFrame
    ## Подключаемся к БД nutrition
    DB_NAME = "oncology_nutrition"
    DB_USER = "nutrition_list"
    DB_PASSWD = "nutrListWhiteForest"
    DB_HOST = "projectswhynot.site"
    connection = connect(host=DB_HOST,
                    user=DB_USER,
                    password=DB_PASSWD,
                    database=DB_NAME,
                    port=11459)
    cursor = connection.cursor()
    cursor.execute(get_by_tags(polim,caloric,special,vol,is_enternal, sip_tube))

    nutr_search_res = DataFrame(cursor.fetchall())
    nutr_search_res.columns = cursor.column_names

    cursor.execute(get_nutrient_tags())

    nutr_tags = DataFrame(cursor.fetchall())
    nutr_tags.columns = cursor.column_names

    cursor.execute(get_PFCE_mash_positive())

    PFCE_values_mash= DataFrame(cursor.fetchall())
    PFCE_values_mash.columns = cursor.column_names

    ##Слияние датавреймов чтобы было нормально и читаемо
    P_values=PFCE_values_mash[PFCE_values_mash['name']=='Белок/100мл']
    F_values=PFCE_values_mash[PFCE_values_mash['name']=='Жиры/100мл']
    C_values=PFCE_values_mash[PFCE_values_mash['name']=='Углеводы/100мл']
    E_values=PFCE_values_mash[(PFCE_values_mash['name']=='Ккал/100мл') | (PFCE_values_mash['name']=='ККал/100мл')]
    PFCE_values=pd.merge(pd.merge(P_values,F_values,on='nutrient_id'),pd.merge(C_values,E_values,on='nutrient_id'),on='nutrient_id')

    ##Слияние всего в сводную таблицу
    data=pd.merge(pd.merge(nutr_search_res,PFCE_values,on='nutrient_id'),nutr_tags,on='nutrient_id')
    data=data.rename(columns={"name": "Название", "manufacturer": "Производитель", "is_enteral": "ЭП/ПЭП", "value_x_x":"Белков в 100 мл", "value_y_x":"Жиров в 100 мл","value_x_y":"Углеводов в 100 мл","value_y_y":"ККал в 100 мл", "all tags": "Характеристики","is_available": "Наличие в клинике"})
    data=data.drop(['feature_id_x_x', 'name_x_x','nutrient_id','feature_id_y_x', 'name_y_x', 'feature_id_x_y', 'name_x_y','feature_id_y_y', 'name_y_y'], axis=1)
    cols=['Название',
    'Производитель',
    'ЭП/ПЭП',
    'Белков в 100 мл',
    'Жиров в 100 мл',
    'Углеводов в 100 мл',
    'ККал в 100 мл',
    'Характеристики',
    'Наличие в клинике']
    data = data[cols]

    ## Делаем nutr удобоваримым для POST
    nutr=[]
    for i in range(len(data)):
        nutr.append(list(data.iloc[i]))

    from flask import Flask, request, render_template
    app = Flask(__name__)
    @app.route('/', methods =["GET"])
    def index():
        return render_template("index1.html", nutritions=nutr)
    if __name__=='__main__':
        app.run()

def read_params(input_str):
    is_enternal={
    "both":'0,1',
    "en":"1",
    "pen":"0"}

    caloric={
    "both":'5,6,7',
    "iso":"5",
    "hyper":"6",
    "hypo":"7"
    }

    polim={
    "both":'3,4',
    "poly":"3",
    "olyg":"4"}


    sip_tube={
        "both":"1,2",
        "sip":"1",
        "tubr":"2"
    }

    special={
    "both":"21, 10, 11, 12, 13",
    "stand":"10",
    "renal":"11",
    "hepa":"12",
    "pulm":"13",
    "diab":"14"
    }
    vol={
    "both":'8,9',
    "fiber":"8",
    "no_fiber":"9"
    }

    for_dict = input_str.split(',')


    db_values=[]
    db_values.append(is_enternal.get(for_dict[0]))
    db_values.append(caloric.get(for_dict[1]))
    db_values.append(polim.get(for_dict[2]))
    db_values.append(sip_tube.get(for_dict[3]))
    db_values.append(special.get(for_dict[4]))
    db_values.append(vol.get(for_dict[5]))
    return(list(db_values))

def db_nutr_table(is_enternal,caloric,polim,sip_tube,special,vol):
    #from util_db_nutr import get_by_tags, get_nutrient_tags, get_PFCE_mash_positive
    import mysql.connector
    from mysql.connector import connect, Error
    import pandas as pd
    from pandas import DataFrame
    ## Подключаемся к БД nutrition
    DB_NAME = "oncology_nutrition"
    DB_USER = "nutrition_list"
    DB_PASSWD = "nutrListWhiteForest"
    DB_HOST = "projectswhynot.site"
    connection = connect(host=DB_HOST,
                    user=DB_USER,
                    password=DB_PASSWD,
                    database=DB_NAME,
                    port=11459)
    cursor = connection.cursor()
    cursor.execute(get_by_tags(polim,caloric,special,vol,is_enternal, sip_tube))

    nutr_search_res = DataFrame(cursor.fetchall())
    nutr_search_res.columns = cursor.column_names

    cursor.execute(get_nutrient_tags())

    nutr_tags = DataFrame(cursor.fetchall())
    nutr_tags.columns = cursor.column_names

    cursor.execute(get_PFCE_mash_positive())

    PFCE_values_mash= DataFrame(cursor.fetchall())
    PFCE_values_mash.columns = cursor.column_names

    ##Слияние датавреймов чтобы было нормально и читаемо
    P_values=PFCE_values_mash[PFCE_values_mash['name']=='Белок/100мл']
    F_values=PFCE_values_mash[PFCE_values_mash['name']=='Жиры/100мл']
    C_values=PFCE_values_mash[PFCE_values_mash['name']=='Углеводы/100мл']
    E_values=PFCE_values_mash[(PFCE_values_mash['name']=='Ккал/100мл') | (PFCE_values_mash['name']=='ККал/100мл')]
    PFCE_values=pd.merge(pd.merge(P_values,F_values,on='nutrient_id'),pd.merge(C_values,E_values,on='nutrient_id'),on='nutrient_id')

    ##Слияние всего в сводную таблицу
    data=pd.merge(pd.merge(nutr_search_res,PFCE_values,on='nutrient_id'),nutr_tags,on='nutrient_id')
    data=data.drop(['feature_id_x_x', 'name_x_x', 'feature_id_y_x', 'name_y_x', 'feature_id_x_y', 'name_x_y','feature_id_y_y', 'name_y_y'], axis=1)
    data.to_csv("data.csv", index=False)
    data=data.rename(columns={'nutrient_id': "ID", "name": "Название", "manufacturer": "Производитель", "is_enteral": "ЭП/ПЭП", "value_x_x":"Белков в 100 мл", "value_y_x":"Жиров в 100 мл","value_x_y":"Углеводов в 100 мл","value_y_y":"ККал в 100 мл", "all tags": "Характеристики","is_available": "Наличие в клинике"})
    cols=["ID", 'Название',
    'Производитель',
    'ЭП/ПЭП',
    'Белков в 100 мл',
    'Жиров в 100 мл',
    'Углеводов в 100 мл',
    'ККал в 100 мл',
    'Характеристики',
    'Наличие в клинике']
    data = data[cols]

    return data

    table=pd.read_csv("data.csv")
    all_ids = table['nutrient_id'].tolist()
    return all_ids

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")
global test
@app.route("/get_par_nutr", methods=["POST", "GET"])
def get_par_nutr():
    if request.method == "POST":
        nutr_type = request.form.get["nutr_type"]
        caloric = request.form.get["caloric"]
        polymer = request.form.get["polymer"]
        sip_tube = request.form.get["sip_tube"]
        spec = request.form.get["spec"]
        fiber = request.form.get["fiber"]
        result=f"{nutr_type+caloric}"
        return f"{nutr_type} + {caloric} + {polymer}+ {sip_tube} + {spec} + {fiber}"
    else: 
        nutr_type = request.args.get("nutr_type")
        caloric = request.args.get("caloric")
        polymer = request.args.get("polymer")
        sip_tube = request.args.get("sip_tube")
        spec = request.args.get("spec")
        fiber = request.args.get("fiber")
        test=db_nutr_table(*read_params(f"{nutr_type},{caloric},{polymer},{sip_tube},{spec},{fiber}"))
        nutr=[]
        for i in range(len(test)):
            nutr.append(list(test.iloc[i]))
        return render_template("index.html", nutritions=nutr)

@app.route("/update_db_nutr", methods=["POST"])
def update_db_nutr():
    values = request.values.getlist('CHECKED')
    true_list=np.unique(values)
    import mysql.connector
    from mysql.connector import connect, Error
    ## Подключаемся к БД nutrition
    DB_NAME = "oncology_nutrition"
    DB_USER = "nutrition_list"
    DB_PASSWD = "nutrListWhiteForest"
    DB_HOST = "projectswhynot.site"
    connection = connect(host=DB_HOST, user=DB_USER, password=DB_PASSWD, database=DB_NAME, port=11459)
    cursor = connection.cursor()
    true_ids=', '.join(true_list)
    if true_ids:
        cursor.execute(f"UPDATE nutrition SET is_available = 1 WHERE id in ({true_ids});")
        connection.commit()
    else:
        pass
    table=pd.read_csv("data.csv")
    all_ids = list(map(str, table['nutrient_id'].tolist()))
    false_list=list(set(all_ids) - set(true_list))
    false_ids=', '.join(false_list)
    if false_ids:
        cursor.execute(f"UPDATE nutrition SET is_available = 0 WHERE id in ({false_ids});")
        connection.commit()
    else: 
        pass
    return render_template("final_page.html")
    



if __name__ == "__main__":
    app.run(debug=True)
